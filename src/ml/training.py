"""Leakage-aware temporal training for shared ML models.

The training protocol has four explicit periods:

``train``
    Target dates before ``validation_start``.  Used to estimate any event
    threshold and to fit candidate estimators.
``validation``
    Target dates from ``validation_start`` to before ``test_start``.  Used only
    to compare candidates and select a probability threshold.
``final_train``
    All target dates before ``test_start`` (train + validation).  Used for the
    final fit after model and threshold selection.
``test``
    Target dates at or after ``test_start``.  Untouched until final scoring.

For grouped sequences (for example a storm track), a group is assigned wholly
to the later split when it crosses a boundary, so one storm cannot contribute
training rows and a test row with the same track history.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Sequence

import numpy as np
import pandas as pd

from src.ml.data import Dataset
from src.ml.estimators import (
    DEFAULT_CANDIDATES,
    build_estimator,
    positive_class_probability,
)
from src.ml.evaluation import (
    STATUS_SIGNAL,
    STATUS_WEAK,
    binary_metrics,
    bootstrap_confidence_intervals,
    event_threshold,
    grade_skill,
    label_target,
    persistence_baseline,
    select_threshold,
    threshold_sweep,
    two_by_two_association,
)
from src.ml.features import (
    assert_chronological_split,
    assert_no_leakage,
    feature_frame,
)

ENGINE_VERSION = "shared-ml-engine/1.0.0"


class InsufficientDataError(RuntimeError):
    """Raised when a temporal split cannot support honest evaluation."""


@dataclass(frozen=True)
class TrainingConfig:
    """Configuration for one model."""

    model_id: str
    hazard: str
    target_mode: str  # "binary" | "continuous_high" | "continuous_low"
    validation_start: str
    test_start: str
    event_quantile: float = 0.95
    fixed_threshold: float | None = None
    candidate_models: tuple[str, ...] = DEFAULT_CANDIDATES
    group_column: str | None = None
    label_end_column: str | None = None
    persistence_column: str | None = None
    evidence_tier: str = "baseline"
    intended_use: str = "Research screening only."
    prohibited_use: str = (
        "Not for warnings, evacuation decisions, damage estimates, or any operational use."
    )
    min_train_rows: int = 200
    min_validation_rows: int = 50
    min_test_rows: int = 50
    min_train_events: int = 10
    limitations: tuple[str, ...] = ()
    # Optional diagnostics for association-style evidence.  ``ablation_columns``
    # are removed from a reduced model so the card can show whether the claimed
    # driver adds incremental ranking skill; ``association_exposure`` produces an
    # unadjusted 2x2 description, not a causal estimate.
    ablation_columns: tuple[str, ...] = ()
    association_exposure: str | None = None


@dataclass
class TrainingResult:
    """A fitted pipeline plus the evidence needed for a model card."""

    config: TrainingConfig
    dataset: Dataset
    pipeline: Any
    card: dict[str, Any]
    feature_columns: list[str] = field(default_factory=list)


def _boundary_for_series(series: pd.Series, timestamp: pd.Timestamp) -> pd.Timestamp:
    """Match a timezone-naive configuration boundary to a timezone-aware series."""
    if isinstance(series.dtype, pd.DatetimeTZDtype):
        tz = series.dt.tz
        if timestamp.tzinfo is None:
            return timestamp.tz_localize(tz)
        return timestamp.tz_convert(tz)
    if timestamp.tzinfo is not None:
        return timestamp.tz_localize(None)
    return timestamp


def temporal_split(
    frame: pd.DataFrame,
    *,
    date_column: str,
    validation_start: pd.Timestamp,
    test_start: pd.Timestamp,
    group_column: str | None = None,
    label_end_column: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Return train/validation/test frames with optional group purging."""
    if validation_start >= test_start:
        raise ValueError("validation_start must precede test_start.")
    dates = pd.to_datetime(frame[date_column])
    validation_start = _boundary_for_series(dates, pd.Timestamp(validation_start))
    test_start = _boundary_for_series(dates, pd.Timestamp(test_start))
    if dates.isna().any():
        raise ValueError(f"{date_column!r} contains missing or unparseable dates.")
    assignment = np.where(
        dates < validation_start,
        0,
        np.where(dates < test_start, 1, 2),
    ).astype(int)
    purge: dict[str, Any] = {"group_column": group_column, "purged_groups": 0, "label_end_column": label_end_column, "purged_label_window_rows": 0}
    if group_column:
        if group_column not in frame.columns:
            raise ValueError(f"Group column {group_column!r} is absent.")
        group_keys = frame[group_column].astype(str)
        group_max = pd.to_datetime(frame[date_column]).groupby(group_keys).transform("max")
        # A group touching the test era belongs wholly to test; a group touching
        # the validation era belongs at least to validation.
        assignment = np.where(group_max >= test_start, 2, assignment)
        assignment = np.where(
            (group_max >= validation_start) & (assignment < 2),
            1,
            assignment,
        )
        original = np.where(
            dates < validation_start,
            0,
            np.where(dates < test_start, 1, 2),
        ).astype(int)
        purge["purged_groups"] = int(
            group_keys[assignment != original].nunique()
        )

    if label_end_column:
        if label_end_column not in frame.columns:
            raise ValueError(f"Label-window end column {label_end_column!r} is absent.")
        label_ends = pd.to_datetime(frame[label_end_column])
        if label_ends.isna().any():
            raise ValueError(f"{label_end_column!r} contains missing or unparseable dates.")
        label_ends = label_ends.map(lambda value: _boundary_for_series(label_ends, value))
        train_crosses = (assignment == 0) & (label_ends >= validation_start)
        validation_crosses = (assignment == 1) & (label_ends >= test_start)
        purge["purged_train_label_window_rows"] = int(train_crosses.sum())
        purge["purged_validation_label_window_rows"] = int(validation_crosses.sum())
        purge["purged_label_window_rows"] = int(train_crosses.sum() + validation_crosses.sum())
        assignment = np.where(train_crosses | validation_crosses, -1, assignment)

    train = frame.loc[assignment == 0].copy()
    validation = frame.loc[assignment == 1].copy()
    test = frame.loc[assignment == 2].copy()
    return train, validation, test, purge


def _require_split(
    name: str,
    part: pd.DataFrame,
    *,
    min_rows: int,
    min_events: int | None = None,
) -> None:
    if len(part) < min_rows:
        raise InsufficientDataError(
            f"{name} has {len(part)} rows; at least {min_rows} are required."
        )
    if min_events is not None and int(part["_label"].sum()) < min_events:
        raise InsufficientDataError(
            f"{name} has {int(part['_label'].sum())} positive events; "
            f"at least {min_events} are required."
        )
    if part["_label"].nunique() < 2 and name in {"train", "validation"}:
        raise InsufficientDataError(f"{name} contains only one class.")


def train_model(dataset: Dataset, config: TrainingConfig) -> TrainingResult:
    """Train, select and evaluate one binary model on a temporal holdout."""
    frame = dataset.frame.copy()
    if dataset.target_column not in frame.columns:
        raise ValueError(f"Target {dataset.target_column!r} is absent from {dataset.name}.")
    features, feature_columns = feature_frame(dataset)
    order = np.argsort(
        pd.to_datetime(frame[dataset.date_column]).to_numpy(), kind="mergesort"
    )
    frame = frame.iloc[order].reset_index(drop=True)
    features = features.iloc[order].reset_index(drop=True)

    validation_start = pd.Timestamp(config.validation_start)
    test_start = pd.Timestamp(config.test_start)
    if config.target_mode not in {"binary", "continuous_high", "continuous_low"}:
        raise ValueError(f"Unsupported target_mode: {config.target_mode!r}")

    if config.target_mode == "binary":
        target_values = pd.to_numeric(frame[dataset.target_column], errors="coerce")
        threshold = float(config.fixed_threshold if config.fixed_threshold is not None else 0.5)
        direction = "high"
        event_definition = (
            f"{dataset.target_column} >= {threshold:g}"
        )
    else:
        direction = "high" if config.target_mode == "continuous_high" else "low"
        target_values = pd.to_numeric(frame[dataset.target_column], errors="coerce")
        date_series = pd.to_datetime(frame[dataset.date_column])
        training_mask = date_series < _boundary_for_series(date_series, validation_start)
        training_values = target_values.loc[training_mask].dropna()
        if config.fixed_threshold is not None:
            threshold = float(config.fixed_threshold)
        else:
            threshold = event_threshold(
                training_values,
                quantile=config.event_quantile,
                direction=direction,
            )
        comparator = ">=" if direction == "high" else "<="
        event_definition = (
            f"{dataset.target_column} {comparator} {threshold:.6g} "
            f"(training-period {config.event_quantile:.3f} quantile)"
        )

    valid_target = target_values.notna().to_numpy()
    frame = frame.loc[valid_target].reset_index(drop=True)
    features = features.loc[valid_target].reset_index(drop=True)
    target_values = target_values.loc[valid_target].reset_index(drop=True)
    frame["_label"] = label_target(
        target_values.to_numpy(),
        threshold=threshold,
        direction=direction,
    )

    train, validation, test, purge = temporal_split(
        frame,
        date_column=dataset.date_column,
        validation_start=validation_start,
        test_start=test_start,
        group_column=config.group_column,
        label_end_column=config.label_end_column,
    )
    _require_split("train", train, min_rows=config.min_train_rows, min_events=config.min_train_events)
    _require_split(
        "validation",
        validation,
        min_rows=config.min_validation_rows,
        min_events=config.min_train_events,
    )
    _require_split("test", test, min_rows=config.min_test_rows, min_events=10)
    assert_chronological_split(
        train,
        validation,
        test,
        date_column=dataset.date_column,
    )

    train_features = features.loc[train.index, feature_columns]
    validation_features = features.loc[validation.index, feature_columns]
    test_features = features.loc[test.index, feature_columns]
    train_labels = train["_label"].to_numpy()
    validation_labels = validation["_label"].to_numpy()
    test_labels = test["_label"].to_numpy()

    candidates: list[dict[str, Any]] = []
    fitted_candidates: dict[str, Any] = {}
    for model_type in config.candidate_models:
        model = build_estimator(model_type)
        model.fit(train_features, train_labels)
        probabilities = positive_class_probability(model, validation_features)
        selected = select_threshold(validation_labels, probabilities)
        from sklearn.metrics import average_precision_score, roc_auc_score

        validation_roc = (
            float(roc_auc_score(validation_labels, probabilities))
            if np.unique(validation_labels).size == 2
            else None
        )
        validation_ap = (
            float(average_precision_score(validation_labels, probabilities))
            if np.unique(validation_labels).size == 2
            else None
        )
        candidates.append(
            {
                "model_type": model_type,
                "validation_roc_auc": validation_roc,
                "validation_average_precision": validation_ap,
                "selected_probability_threshold": selected["threshold"],
                "validation_precision": selected["precision"],
                "validation_recall": selected["recall"],
                "validation_f1": selected["f1"],
                "validation_balanced_accuracy": selected["balanced_accuracy"],
                "validation_predicted_positive_rate": selected["predicted_positive_rate"],
            }
        )
        fitted_candidates[model_type] = model

    def candidate_score(item: dict[str, Any]) -> tuple[float, float, float]:
        return (
            item["validation_average_precision"]
            if item["validation_average_precision"] is not None
            else -1.0,
            item["validation_roc_auc"] if item["validation_roc_auc"] is not None else -1.0,
            item["validation_f1"],
        )

    selected_candidate = max(candidates, key=candidate_score)
    selected_model_type = selected_candidate["model_type"]
    probability_threshold = selected_candidate["selected_probability_threshold"]

    final_train = pd.concat([train, validation], axis=0).sort_values(
        dataset.date_column
    )
    # Preserve the original row index so the feature matrix stays aligned.
    final_train_features = features.loc[final_train.index, feature_columns]
    final_train_labels = final_train["_label"].to_numpy()
    if np.unique(final_train_labels).size < 2:
        raise InsufficientDataError("Final training period contains only one class.")

    final_model = build_estimator(selected_model_type)
    final_model.fit(final_train_features, final_train_labels)
    test_probabilities = positive_class_probability(final_model, test_features)
    train_prevalence = float(final_train_labels.mean())
    metrics = binary_metrics(
        test_labels,
        test_probabilities,
        threshold=probability_threshold,
        train_prevalence=train_prevalence,
    )
    metrics["bootstrap_95ci"] = bootstrap_confidence_intervals(
        test_labels,
        test_probabilities,
        threshold=probability_threshold,
    )
    # Score validation thresholds with the candidate fitted on train only; the
    # final model has already seen validation rows, so its validation output
    # would overstate selection performance.
    metrics["validation_threshold_scores"] = threshold_sweep(
        validation_labels,
        positive_class_probability(fitted_candidates[selected_model_type], validation_features),
    )
    persistence = None
    if config.persistence_column and config.persistence_column in test.columns:
        persistence = persistence_baseline(
            test_labels,
            test[config.persistence_column].to_numpy(),
            threshold=threshold,
            direction=direction,
        )
    metrics["persistence_baseline"] = persistence
    if config.ablation_columns:
        metrics["ablation"] = _ablation_diagnostics(
            feature_columns=feature_columns,
            excluded_columns=config.ablation_columns,
            model_type=selected_model_type,
            final_train_features=final_train_features,
            final_train_labels=final_train_labels,
            test_features=test_features,
            test_labels=test_labels,
            threshold=probability_threshold,
            train_prevalence=train_prevalence,
        )
    if config.association_exposure:
        metrics["association_analysis"] = {
            "final_train": two_by_two_association(
                final_train[config.association_exposure].to_numpy(),
                final_train_labels,
                exposure_name=config.association_exposure,
            ),
            "test": two_by_two_association(
                test[config.association_exposure].to_numpy(),
                test_labels,
                exposure_name=config.association_exposure,
            ),
        }

    skill = grade_skill(metrics)
    final_status = skill["status"]
    final_reason = skill["reason"]
    if (
        config.evidence_tier == "exploratory_association"
        and skill["status"] in {STATUS_WEAK, STATUS_SIGNAL}
    ):
        final_status = "EXPLORATORY_ASSOCIATION"
        final_reason = (
            "Exploratory concurrent association only; no forecast lead time and "
            "no joint-probability or impact interpretation. " + skill["reason"]
        )
    feature_ranges = _feature_ranges(final_train_features)
    limitations = _limitations(dataset, config, skill)
    persistence = metrics.get("persistence_baseline")
    if (
        isinstance(persistence, dict)
        and persistence.get("available")
        and metrics.get("f1") is not None
        and persistence.get("f1") is not None
        and metrics["f1"] <= persistence["f1"] + 1e-9
    ):
        limitations.insert(
            0,
            "At the validation-selected threshold, held-out F1 "
            f"({metrics['f1']:.3f}) does not exceed the simple persistence baseline "
            f"({persistence['f1']:.3f}); the model is not an improvement over persistence "
            "for this event definition.",
        )
    trained_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    card: dict[str, Any] = {
        "schema_version": 1,
        "engine_version": ENGINE_VERSION,
        "model_id": config.model_id,
        "hazard": config.hazard,
        "dataset_name": dataset.name,
        "target_column": dataset.target_column,
        "target_mode": config.target_mode,
        "target_definition": event_definition,
        "target_threshold": threshold,
        "target_direction": direction,
        "threshold_source": (
            "training target dates only (< validation_start)"
            if config.target_mode != "binary"
            else "fixed binary label"
        ),
        "evidence_tier": config.evidence_tier,
        "status": final_status,
        "skill_grade": skill["status"],
        "status_reason": final_reason,
        "validation_status": "SINGLE_TEMPORAL_HOLDOUT_NOT_INDEPENDENTLY_VALIDATED",
        "trained_at_utc": trained_at,
        "selected_model_type": selected_model_type,
        "selected_probability_threshold": probability_threshold,
        "model_selection_metric": (
            "Validation average precision (primary), then validation ROC-AUC, then F1; "
            "decision threshold selected by validation F1 with recall/precision tie-breaks."
        ),
        "candidate_selection": candidates,
        "validation_rows": int(len(validation)),
        "validation_events": int(validation_labels.sum()),
        "final_train_rows": int(len(final_train)),
        "final_train_events": int(final_train_labels.sum()),
        "test_rows": int(len(test)),
        "test_events": int(test_labels.sum()),
        "train_prevalence": train_prevalence,
        "test_prevalence": float(test_labels.mean()),
        "temporal_split": {
            "train_target_dates_before": str(validation_start.date()),
            "validation_target_dates": (
                f"{validation_start.date()} through before {test_start.date()}"
            ),
            "final_train_target_dates_before": str(test_start.date()),
            "test_target_dates_from": str(test_start.date()),
            "grouped_purge": purge,
        },
        "feature_columns": feature_columns,
        "feature_count": len(feature_columns),
        "feature_ranges": feature_ranges,
        "metrics": metrics,
        "provenance": dataset.provenance,
        "notes": list(dataset.notes),
        "limitations": limitations,
        "intended_use": config.intended_use,
        "prohibited_use": config.prohibited_use,
        "artifact": {
            "path": f"models/ml/{config.model_id}/model.joblib",
            "format": "joblib-pipeline",
            "loader": "src.ml.inference.predict_from_context",
        },
    }
    return TrainingResult(
        config=config,
        dataset=dataset,
        pipeline=final_model,
        card=card,
        feature_columns=feature_columns,
    )


def _ablation_diagnostics(
    *,
    feature_columns: list[str],
    excluded_columns: tuple[str, ...],
    model_type: str,
    final_train_features: pd.DataFrame,
    final_train_labels: np.ndarray,
    test_features: pd.DataFrame,
    test_labels: np.ndarray,
    threshold: float,
    train_prevalence: float,
) -> dict[str, Any]:
    """Compare the full model with a reduced model that removes claimed drivers."""
    kept = [name for name in feature_columns if name not in set(excluded_columns)]
    removed = [name for name in feature_columns if name in set(excluded_columns)]
    if not kept:
        return {"available": False, "reason": "Ablation removed every feature."}
    reduced = build_estimator(model_type)
    reduced.fit(final_train_features[kept], final_train_labels)
    probabilities = positive_class_probability(reduced, test_features[kept])
    reduced_metrics = binary_metrics(
        test_labels,
        probabilities,
        threshold=threshold,
        train_prevalence=train_prevalence,
    )
    from sklearn.metrics import average_precision_score, roc_auc_score

    full_probabilities = positive_class_probability(
        build_estimator(model_type).fit(final_train_features, final_train_labels),
        test_features,
    )
    full_roc = (
        float(roc_auc_score(test_labels, full_probabilities))
        if np.unique(test_labels).size == 2
        else None
    )
    full_ap = (
        float(average_precision_score(test_labels, full_probabilities))
        if np.unique(test_labels).size == 2
        else None
    )
    reduced_ap = reduced_metrics.get("average_precision")
    return {
        "available": True,
        "excluded_columns": removed,
        "kept_feature_count": len(kept),
        "full_test_roc_auc": full_roc,
        "full_test_average_precision": full_ap,
        "reduced_test_roc_auc": reduced_metrics.get("roc_auc"),
        "reduced_test_average_precision": reduced_ap,
        "delta_average_precision": (
            float(full_ap - reduced_ap)
            if full_ap is not None and reduced_ap is not None
            else None
        ),
        "interpretation": (
            "If the reduced model performs similarly, the excluded variables have "
            "no demonstrated incremental ranking skill on this holdout."
        ),
    }


def _feature_ranges(features: pd.DataFrame) -> dict[str, dict[str, Any]]:
    ranges: dict[str, dict[str, Any]] = {}
    for column in features.columns:
        values = pd.to_numeric(features[column], errors="coerce")
        finite = values[np.isfinite(values)]
        ranges[str(column)] = {
            "min": float(finite.min()) if len(finite) else None,
            "max": float(finite.max()) if len(finite) else None,
            "median": float(finite.median()) if len(finite) else None,
            "missing_fraction": float(values.isna().mean()),
        }
    return ranges


def _limitations(
    dataset: Dataset,
    config: TrainingConfig,
    skill: dict[str, str],
) -> list[str]:
    limitations = list(config.limitations)
    limitations.extend(dataset.notes)
    limitations.extend(
        [
            "A single chronological holdout is preliminary evidence, not independent validation.",
            "No calibration, geographic transferability, drift or operational-readiness claim is made.",
            f"Skill grade is {skill['status']}: {skill['reason']}",
            "The model card records the exact threshold, features and split; changing any of them requires retraining and re-evaluation.",
        ]
    )
    # De-duplicate while preserving order.
    return list(dict.fromkeys(limitations))


def train_all(datasets_and_configs: Sequence[tuple[Dataset, TrainingConfig]]) -> tuple[list[TrainingResult], dict[str, str]]:
    """Train a collection, returning successes and explicit failures."""
    results: list[TrainingResult] = []
    errors: dict[str, str] = {}
    for dataset, config in datasets_and_configs:
        try:
            results.append(train_model(dataset, config))
        except (InsufficientDataError, ValueError, RuntimeError) as exc:
            errors[config.model_id] = f"{type(exc).__name__}: {exc}"
    return results, errors


__all__ = [
    "ENGINE_VERSION",
    "InsufficientDataError",
    "TrainingConfig",
    "TrainingResult",
    "temporal_split",
    "train_all",
    "train_model",
]
