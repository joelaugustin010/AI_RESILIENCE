"""Feature contract, leakage guards and context validation.

The engine treats the feature list in a model card as a contract.  A feature is
rejected when it is the target itself, carries a target/future marker, is a
datetime/identifier, is duplicated, or is absent from the frame.  Inference
uses the same contract, so a model cannot silently accept a different column
order or an invented value.
"""

from __future__ import annotations

from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd

from src.ml.data import Dataset

TARGET_PREFIX = "target_"
# Tokens that indicate a column describes the outcome or a future observation.
# They are deliberately conservative: a false positive is easier to review than
# a leaked feature.
FORBIDDEN_FEATURE_TOKENS: tuple[str, ...] = (
    "future",
    "nextday",
    "next_day",
    "outcome",
    "label",
    "truth",
)
IDENTIFIER_COLUMNS = {
    "date",
    "time",
    "target_date",
    "location",
    "storm_id",
    "event_id",
    "index",
}


class LeakageError(ValueError):
    """Raised when a feature list could leak the target or a future value."""


class FeatureContractError(ValueError):
    """Raised when inference context does not satisfy a model feature contract."""


def assert_no_leakage(
    feature_columns: Sequence[str],
    target_column: str,
    *,
    date_column: str | None = None,
    frame: pd.DataFrame | None = None,
) -> list[str]:
    """Validate a feature list and return it as a list.

    Parameters
    ----------
    feature_columns:
        Candidate predictors.
    target_column:
        The outcome column that must never appear as a predictor.
    date_column:
        The split/target date column, which must also never be a predictor.
    frame:
        Optional frame used to check presence, uniqueness and numeric dtype.
    """
    features = [str(column) for column in feature_columns]
    if not features:
        raise LeakageError("A model must declare at least one predictor.")
    if target_column in features:
        raise LeakageError(f"Target column {target_column!r} cannot be a predictor.")
    if date_column is not None and date_column in features:
        raise LeakageError(f"Date column {date_column!r} cannot be a predictor.")

    duplicated = sorted({name for name in features if features.count(name) > 1})
    if duplicated:
        raise LeakageError(f"Duplicate predictor columns: {duplicated}")

    for name in features:
        lowered = name.casefold()
        if lowered.startswith(TARGET_PREFIX):
            raise LeakageError(f"Target-prefixed predictor is not allowed: {name!r}")
        if any(token in lowered for token in FORBIDDEN_FEATURE_TOKENS):
            raise LeakageError(
                f"Predictor {name!r} looks like a future outcome; refusing leakage-prone feature."
            )
        if lowered in IDENTIFIER_COLUMNS:
            raise LeakageError(f"Identifier/date column cannot be a predictor: {name!r}")

    if frame is not None:
        missing = [name for name in features if name not in frame.columns]
        if missing:
            raise LeakageError(f"Predictors missing from the frame: {missing}")
        non_numeric = [
            name
            for name in features
            if not pd.api.types.is_numeric_dtype(frame[name])
        ]
        if non_numeric:
            raise LeakageError(
                f"Predictors must be numeric; non-numeric columns: {non_numeric}"
            )
    return features


def feature_frame(
    dataset: Dataset,
    *,
    feature_columns: Sequence[str] | None = None,
) -> tuple[pd.DataFrame, list[str]]:
    """Return the numeric design matrix and its validated feature names."""
    features = assert_no_leakage(
        feature_columns if feature_columns is not None else dataset.feature_columns,
        dataset.target_column,
        date_column=dataset.date_column,
        frame=dataset.frame,
    )
    frame = dataset.frame[features].copy()
    frame = frame.replace([np.inf, -np.inf], np.nan)
    return frame, features


def assert_chronological_split(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    test: pd.DataFrame,
    *,
    date_column: str,
) -> None:
    """Assert non-empty, ordered temporal splits with no date overlap."""
    for name, part in (("train", train), ("validation", validation), ("test", test)):
        if part.empty:
            raise ValueError(f"The {name} split is empty.")
        if not pd.api.types.is_datetime64_any_dtype(part[date_column]):
            raise ValueError(f"{date_column!r} must be a datetime column for {name}.")
    if train[date_column].max() >= validation[date_column].min():
        raise ValueError("Training target dates overlap or follow validation target dates.")
    if validation[date_column].max() >= test[date_column].min():
        raise ValueError("Validation target dates overlap or follow test target dates.")
    if train[date_column].max() >= test[date_column].min():
        raise ValueError("Training target dates overlap or follow test target dates.")


def context_from_inputs(
    feature_columns: Sequence[str],
    inputs: dict[str, Any] | None,
) -> dict[str, float]:
    """Extract a model context from an explicit ``ml_context`` mapping.

    Only exact feature names are accepted.  A few unambiguous aliases are
    supported for interactive use.  Values are never estimated, defaulted or
    copied from a similarly named field.
    """
    if not inputs:
        return {}
    raw = inputs.get("ml_context")
    if raw is None:
        raw = inputs
    if not isinstance(raw, dict):
        raise FeatureContractError("ml_context must be a mapping of feature names to values.")
    aliases = {
        "wind_speed_kt": "wind_kt",
        "wind_kt": "wind_kt",
        "pressure_hpa": "pressure_hpa",
        "latitude": "latitude",
        "longitude": "longitude",
        "magnitude": "magnitude",
        "depth_km": "depth_km",
    }
    context: dict[str, float] = {}
    for name in feature_columns:
        value = raw.get(name)
        if value is None and name in aliases:
            value = raw.get(aliases[name])
        if value is None or value == "":
            continue
        if isinstance(value, bool):
            raise FeatureContractError(f"{name} must be a finite number, not a boolean.")
        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError) as exc:
            raise FeatureContractError(f"{name} must be a finite number.") from exc
        if not np.isfinite(number):
            raise FeatureContractError(f"{name} must be a finite number.")
        context[name] = number
    return context


def missing_context_fields(
    feature_columns: Iterable[str],
    context: dict[str, Any],
) -> list[str]:
    """Return required feature names absent from a context mapping."""
    return [name for name in feature_columns if name not in context]
