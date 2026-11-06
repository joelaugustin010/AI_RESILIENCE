"""Fail-closed inference over the shared model registry.

Inference is only performed when every feature in the model card is supplied as
a finite number.  Missing context is reported, never imputed from unrelated
inputs.  Models graded ``NO_SKILL`` or ``INSUFFICIENT_TEST_EVENTS`` are loaded
for inspection but cannot produce a decision output.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from src.ml.features import (
    FeatureContractError,
    missing_context_fields,
)
from src.ml.monitoring import missingness_warnings, range_warnings
from src.ml.persistence import load_artifact
from src.ml.registry import card_consistency_problems, load_model_card

USABLE_STATUSES = {"WEAK_RESEARCH_SIGNAL", "RESEARCH_SIGNAL_NOT_VALIDATED"}


class ModelNotUsableError(RuntimeError):
    """Raised when a registered model cannot support an inference output."""


class InferenceInputError(ValueError):
    """Raised when inference context violates the feature contract."""


def required_context_fields(card: dict[str, Any]) -> list[str]:
    features = card.get("feature_columns")
    if not isinstance(features, list):
        raise InferenceInputError("Model card has no feature contract.")
    return [str(name) for name in features]


def context_gaps(card: dict[str, Any], context: dict[str, Any]) -> list[str]:
    return missing_context_fields(required_context_fields(card), context)


def _context_frame(card: dict[str, Any], context: dict[str, Any]) -> pd.DataFrame:
    features = required_context_fields(card)
    row: dict[str, float] = {}
    for name in features:
        if name not in context:
            raise InferenceInputError(f"Missing required feature {name!r}.")
        value = context[name]
        if isinstance(value, bool):
            raise InferenceInputError(f"{name} must be a finite number, not a boolean.")
        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError) as exc:
            raise InferenceInputError(f"{name} must be a finite number.") from exc
        if not np.isfinite(number):
            raise InferenceInputError(f"{name} must be a finite number.")
        row[name] = number
    return pd.DataFrame([row], columns=features)


def predict_from_context(
    model_id: str,
    context: dict[str, Any],
    *,
    allow_weak_signal: bool = True,
    allow_no_skill: bool = False,
) -> dict[str, Any]:
    """Run one registered model with a complete, explicit context."""
    card = load_model_card(model_id)
    if card is None:
        raise ModelNotUsableError(f"Model {model_id!r} is not registered.")
    problems = card_consistency_problems(card)
    if problems:
        raise ModelNotUsableError(
            f"Model card {model_id!r} is unusable: {'; '.join(problems)}"
        )
    validity = str(card.get("evaluation_validity") or "")
    if validity.startswith("INVALIDATED_"):
        raise ModelNotUsableError(
            f"Model {model_id!r} has invalidated evaluation provenance ({validity}); "
            "no inference is permitted until it is retrained and reevaluated."
        )
    status = card.get("status")
    if status == "NO_SKILL" and not allow_no_skill:
        raise ModelNotUsableError(
            f"Model {model_id!r} was graded NO_SKILL on its temporal holdout; "
            "no decision output is produced."
        )
    if status == "INSUFFICIENT_TEST_EVENTS" and not allow_no_skill:
        raise ModelNotUsableError(
            f"Model {model_id!r} has too few held-out events for a decision output."
        )
    if status == "WEAK_RESEARCH_SIGNAL" and not allow_weak_signal:
        raise ModelNotUsableError(
            f"Model {model_id!r} is a weak research signal and weak output is disabled."
        )

    gaps = context_gaps(card, context)
    if gaps:
        raise InferenceInputError(
            f"Model {model_id!r} requires {len(gaps)} more context feature(s): "
            f"{', '.join(gaps[:12])}{' …' if len(gaps) > 12 else ''}"
        )
    frame = _context_frame(card, context)
    pipeline = load_artifact(model_id)
    if not hasattr(pipeline, "predict_proba"):
        raise ModelNotUsableError(f"Artifact for {model_id!r} has no predict_proba.")
    classifier = pipeline.steps[-1][1]
    classes = list(getattr(classifier, "classes_", []))
    if 1 not in classes:
        raise ModelNotUsableError(f"Artifact for {model_id!r} has no positive class.")
    probabilities = pipeline.predict_proba(frame)[:, classes.index(1)]
    score = float(probabilities[0])
    threshold = float(card.get("selected_probability_threshold", 0.5))
    metrics = card.get("metrics", {})
    warnings = range_warnings(card, context) + missingness_warnings(card, context)
    if status == "WEAK_RESEARCH_SIGNAL":
        warnings.append(
            "This model was graded a weak research signal; its output is not a reliable event forecast."
        )
    if not np.isfinite(score) or not 0.0 <= score <= 1.0:
        raise ModelNotUsableError(f"Model {model_id!r} produced an invalid probability.")
    return {
        "model_id": model_id,
        "hazard": card.get("hazard"),
        "evidence_tier": card.get("evidence_tier"),
        "status": status,
        "validation_status": card.get("validation_status"),
        "probability_estimate": score,
        "selected_probability_threshold": threshold,
        "event_flag_at_threshold": bool(score >= threshold),
        "score_interpretation": (
            "Model probability estimate for the documented research event. "
            "It is not a calibrated probability of harm, loss, or an official warning."
        ),
        "calibration": {
            "brier_score": metrics.get("brier_score"),
            "expected_calibration_error": metrics.get("expected_calibration_error"),
            "base_rate_brier_score": metrics.get("base_rate_brier_score"),
        },
        "baselines": {
            "majority_baseline": metrics.get("majority_baseline"),
            "persistence_baseline": metrics.get("persistence_baseline"),
        },
        "target_definition": card.get("target_definition"),
        "intended_use": card.get("intended_use"),
        "prohibited_use": card.get("prohibited_use"),
        "warnings": list(dict.fromkeys(warnings)),
        "limitations": list(card.get("limitations", [])),
    }


__all__ = [
    "InferenceInputError",
    "ModelNotUsableError",
    "USABLE_STATUSES",
    "context_gaps",
    "predict_from_context",
    "required_context_fields",
]


def predict_regression_from_context(model_id: str, context: dict[str, Any]) -> dict[str, Any]:
    """Fail-closed inference for a registered continuous regression model."""
    card = load_model_card(model_id)
    if card is None or card.get("task_type") != "regression":
        raise ModelNotUsableError(f"Model {model_id!r} is not a registered regression model.")
    if str(card.get("evaluation_validity") or "").startswith("INVALIDATED_"):
        raise ModelNotUsableError(f"Model {model_id!r} has invalidated evaluation provenance.")
    if card.get("status") not in USABLE_STATUSES:
        raise ModelNotUsableError(f"Model {model_id!r} has status {card.get('status')!r}; regression inference is blocked.")
    problems = card_consistency_problems(card)
    if problems:
        raise ModelNotUsableError(f"Model card for {model_id!r} is inconsistent: {problems}")
    frame = _context_frame(card, context)
    pipeline = load_artifact(model_id)
    if not hasattr(pipeline, "predict"):
        raise ModelNotUsableError(f"Artifact for {model_id!r} has no predict method.")
    value = float(np.asarray(pipeline.predict(frame), dtype=float)[0])
    if not np.isfinite(value):
        raise ModelNotUsableError(f"Model {model_id!r} produced a non-finite estimate.")
    return {
        "model_id": model_id, "hazard": card.get("hazard"), "task_type": "regression",
        "status": card.get("status"), "estimate": value, "unit": card.get("prediction_unit"),
        "target_definition": card.get("target_definition"),
        "limitations": list(card.get("limitations", [])),
        "warnings": ["Research-only continuous estimate; not a calibrated disaster-risk probability or official forecast."],
    }


__all__ = [
    "InferenceInputError", "ModelNotUsableError", "USABLE_STATUSES",
    "context_gaps", "predict_from_context", "predict_regression_from_context",
    "required_context_fields",
]
