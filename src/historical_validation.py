"""Readiness checks and descriptive metrics for future event validation."""

from __future__ import annotations

import math
import re
from datetime import datetime
from typing import Any, Sequence

import pandas as pd


VALIDATION_FIELDS = {
    "event_id": "Unique event identifier",
    "outcome_source_url": "Independent outcome source URL",
    "outcome_definition": "Documented outcome/label definition",
    "outcome_independent": "Independent outcome review flag",
    "outcome_start": "Outcome start timestamp",
    "outcome_end": "Outcome end timestamp",
    "observation_source_url": "Observation/predictor source URL",
    "observation_time_basis": "Observation timezone/time basis",
    "feature_cutoff": "Feature availability cutoff timestamp",
    "prediction_horizon_hours": "Prediction horizon in hours",
    "geographic_match_method": "Geographic matching method",
    "geographic_match_review": "Independent geographic-match review",
    "temporal_match_method": "Temporal matching method",
    "temporal_match_review": "Independent temporal-match review",
    "dataset_sha256": "Immutable dataset SHA-256",
    "code_version": "Code revision",
    "model_version": "Model/method version",
    "split_assignment": "Predeclared train/validation/test assignment",
}


def historical_validation_readiness(case: dict[str, Any]) -> dict[str, Any]:
    """Fail closed when event labels, matching, time cutoffs, or provenance are missing."""
    blockers = [
        f"Missing {label.lower()}."
        for field, label in VALIDATION_FIELDS.items()
        if case.get(field) is None or str(case.get(field)).strip() == ""
    ]
    if case.get("outcome_independent") is not True:
        blockers.append("Outcome labels must be independently reviewed.")
    if case.get("geographic_match_review") is not True:
        blockers.append("Geographic matching must be independently reviewed.")
    if case.get("temporal_match_review") is not True:
        blockers.append("Temporal matching must be independently reviewed.")

    parsed: dict[str, datetime] = {}
    for field in ("outcome_start", "outcome_end", "feature_cutoff"):
        value = case.get(field)
        if value is None:
            continue
        try:
            parsed[field] = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            blockers.append(f"{field.replace('_', ' ').capitalize()} must be an ISO-8601 timestamp.")
    if "outcome_start" in parsed and "outcome_end" in parsed:
        if parsed["outcome_end"] < parsed["outcome_start"]:
            blockers.append("Outcome end timestamp precedes outcome start timestamp.")
    if "feature_cutoff" in parsed and "outcome_start" in parsed:
        cutoff = parsed["feature_cutoff"]
        event_start = parsed["outcome_start"]
        if cutoff.tzinfo != event_start.tzinfo:
            blockers.append("Feature cutoff and outcome timestamps must use a comparable timezone basis.")
        elif cutoff >= event_start:
            blockers.append("Feature cutoff must precede the outcome window to prevent temporal leakage.")

    horizon = case.get("prediction_horizon_hours")
    try:
        horizon_value = float(horizon)
        if not math.isfinite(horizon_value) or horizon_value <= 0:
            blockers.append("Prediction horizon must be a finite positive number of hours.")
    except (TypeError, ValueError):
        if horizon is not None:
            blockers.append("Prediction horizon must be a finite positive number of hours.")

    digest = str(case.get("dataset_sha256", ""))
    if digest and not re.fullmatch(r"[0-9a-fA-F]{64}", digest):
        blockers.append("Dataset SHA-256 must contain exactly 64 hexadecimal characters.")

    return {
        "ready": not blockers,
        "status": "Ready for review-only evaluation design" if not blockers else "Blocked: validation evidence incomplete",
        "blockers": blockers,
        "scientific_validity": "Not established by this readiness check.",
    }


def evaluate_binary_event_predictions(
    observed: Sequence[int],
    predicted: Sequence[int],
    case_ids: Sequence[str],
) -> dict[str, Any]:
    """Return confusion counts and undefined-safe binary metrics for a held-out set."""
    observed_values = list(observed)
    predicted_values = list(predicted)
    identifiers = list(case_ids)
    if not observed_values or len(observed_values) != len(predicted_values) or len(observed_values) != len(identifiers):
        raise ValueError("Observed labels, predictions, and case IDs must have equal non-zero lengths.")
    if any(value not in (0, 1) for value in [*observed_values, *predicted_values]):
        raise ValueError("Observed labels and predictions must contain only 0 or 1.")
    if any(not str(case_id).strip() for case_id in identifiers):
        raise ValueError("Every evaluated case must have a non-empty ID.")

    tp = fp = tn = fn = 0
    false_positive_ids: list[str] = []
    false_negative_ids: list[str] = []
    for actual, estimate, case_id in zip(observed_values, predicted_values, identifiers):
        if actual == 1 and estimate == 1:
            tp += 1
        elif actual == 0 and estimate == 1:
            fp += 1
            false_positive_ids.append(str(case_id))
        elif actual == 0 and estimate == 0:
            tn += 1
        else:
            fn += 1
            false_negative_ids.append(str(case_id))

    def ratio(numerator: int, denominator: int) -> float | None:
        return numerator / denominator if denominator else None

    precision = ratio(tp, tp + fp)
    recall = ratio(tp, tp + fn)
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and precision + recall
        else None
    )
    return {
        "true_positive": tp,
        "false_positive": fp,
        "true_negative": tn,
        "false_negative": fn,
        "precision": precision,
        "recall_sensitivity": recall,
        "specificity": ratio(tn, tn + fp),
        "f1": f1,
        "accuracy": ratio(tp + tn, len(observed_values)),
        "false_positive_case_ids": false_positive_ids,
        "false_negative_case_ids": false_negative_ids,
        "metric_scope": "Held-out cases only; does not establish generalization or operational utility.",
    }


def historical_validation_checklist() -> pd.DataFrame:
    """List evidence and evaluation stages required before reporting event skill."""
    rows = [
        ("Event identification", "Dated event registry, geographic footprint, and event definition"),
        ("Observation records", "Traceable source, units, timestamps/timezone, QC, and immutable source hash"),
        ("Independent outcomes", "Outcome source distinct from predictors, documented label definition, and independent review"),
        ("Geographic matching", "Documented CRS, spatial method, positional uncertainty, and reviewed match result"),
        ("Temporal matching", "Common time basis, event window, feature cutoff before outcome, and forecast horizon"),
        ("Leakage-safe evaluation", "Predeclared event/time-separated splits; related event records remain in one split"),
        ("Metrics and errors", "Confusion counts, sensitivity, specificity, precision, F1, calibration if probabilistic, and FP/FN case review"),
        ("Reproducibility", "Pinned data hashes, code revision, model/method configuration, and rerunnable evaluation"),
        ("Generalization and bias", "Held-out geography/time coverage, missingness, subgroup performance, and documented limits"),
    ]
    return pd.DataFrame(rows, columns=["Validation stage", "Minimum evidence"])
