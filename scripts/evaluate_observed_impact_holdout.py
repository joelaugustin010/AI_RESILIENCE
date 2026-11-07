"""Evaluate impact predictions against a strictly separated observed holdout CSV.

The script evaluates supplied predictions; it does not train a model or certify
operational validity. The input must contain observed, source-linked outcomes
for held-out events and geographies not used for training.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

REQUIRED_COLUMNS = {
    "observation_id", "event_id", "geography_id", "observation_date",
    "outcome_name", "outcome_value", "predicted_value", "outcome_unit",
    "source_url",
}
REQUIRED_METADATA = {
    "model_id", "model_version", "outcome_definition", "outcome_unit",
    "training_event_ids", "training_geographies", "ground_truth_source",
    "prediction_method", "known_limitations",
}


def evaluate_observed_impact_holdout(
    frame: pd.DataFrame,
    metadata: dict[str, Any],
    *,
    minimum_events: int = 3,
    minimum_geographies: int = 2,
) -> dict[str, Any]:
    """Check independence and score observed-versus-predicted impact records."""
    missing_columns = sorted(REQUIRED_COLUMNS - set(frame.columns))
    missing_metadata = sorted(REQUIRED_METADATA - set(metadata))
    if missing_columns or missing_metadata:
        return {
            "status": "BLOCKED_SCHEMA",
            "problems": [
                *([f"Missing columns: {missing_columns}"] if missing_columns else []),
                *([f"Missing metadata: {missing_metadata}"] if missing_metadata else []),
            ],
            "model_validated": False,
            "evaluation_performed": False,
        }
    if frame.empty:
        return {
            "status": "BLOCKED_EMPTY_HOLDOUT",
            "problems": ["Holdout file contains no observations."],
            "model_validated": False,
            "evaluation_performed": False,
        }
    data = frame.copy()
    problems = []
    for column in ("observation_id", "event_id", "geography_id", "outcome_name", "outcome_unit", "source_url"):
        if data[column].isna().any() or data[column].astype(str).str.strip().eq("").any():
            problems.append(f"{column} must be complete.")
    if data["observation_id"].duplicated().any():
        problems.append("observation_id must be unique.")
    if data.duplicated(["event_id", "geography_id", "outcome_name"]).any():
        problems.append("Duplicate event/geography/outcome rows must be resolved.")
    data["observation_date"] = pd.to_datetime(data["observation_date"], errors="coerce")
    if data["observation_date"].isna().any():
        problems.append("observation_date contains missing or invalid dates.")
    for column in ("outcome_value", "predicted_value"):
        data[column] = pd.to_numeric(data[column], errors="coerce")
        if data[column].isna().any() or not np.isfinite(data[column].to_numpy(dtype=float)).all():
            problems.append(f"{column} must contain finite numeric values.")
        elif (data[column] < 0).any():
            problems.append(f"{column} cannot contain negative impact counts or losses.")
    if data["outcome_name"].nunique(dropna=True) != 1:
        problems.append("A holdout file must contain exactly one outcome definition.")
    if data["outcome_unit"].nunique(dropna=True) != 1:
        problems.append("A holdout file must contain exactly one outcome unit.")
    if data["source_url"].astype(str).str.match(r"^https://").eq(False).any():
        problems.append("Every observed outcome source_url must use HTTPS.")
    if metadata.get("outcome_unit") != (str(data["outcome_unit"].iloc[0]) if len(data) else None):
        problems.append("Metadata outcome_unit does not match the observed holdout.")
    if metadata.get("outcome_definition") != (str(data["outcome_name"].iloc[0]) if len(data) else None):
        problems.append("Metadata outcome_definition does not match the observed holdout.")

    training_events = {str(value) for value in metadata.get("training_event_ids", [])}
    training_geographies = {str(value) for value in metadata.get("training_geographies", [])}
    holdout_events = set(data["event_id"].astype(str))
    holdout_geographies = set(data["geography_id"].astype(str))
    event_overlap = sorted(training_events & holdout_events)
    geography_overlap = sorted(training_geographies & holdout_geographies)
    if event_overlap:
        problems.append(f"Training/holdout event leakage detected: {event_overlap[:10]}.")
    if geography_overlap:
        problems.append(f"Training/holdout geography leakage detected: {geography_overlap[:10]}.")
    if not isinstance(metadata.get("training_event_ids"), list) or not training_events:
        problems.append("Metadata must list the training event IDs.")
    if not isinstance(metadata.get("training_geographies"), list) or not training_geographies:
        problems.append("Metadata must list the training geographies.")
    if len(holdout_events) < minimum_events:
        problems.append(f"At least {minimum_events} independent holdout events are required.")
    if len(holdout_geographies) < minimum_geographies:
        problems.append(f"At least {minimum_geographies} holdout geographies are required.")

    if problems:
        return {
            "status": "BLOCKED_DATA_OR_INDEPENDENCE_GAPS",
            "problems": problems,
            "row_count": int(len(data)),
            "holdout_event_count": int(len(holdout_events)),
            "holdout_geography_count": int(len(holdout_geographies)),
            "training_holdout_event_overlap": event_overlap,
            "training_holdout_geography_overlap": geography_overlap,
            "model_validated": False,
            "evaluation_performed": False,
        }

    actual = data["outcome_value"].to_numpy(dtype=float)
    predicted = data["predicted_value"].to_numpy(dtype=float)
    absolute_error = np.abs(predicted - actual)
    nonzero = actual > 0
    total_actual = float(actual.sum())
    metrics = {
        "n_test": int(len(data)),
        "mae": float(mean_absolute_error(actual, predicted)),
        "rmse": float(math.sqrt(mean_squared_error(actual, predicted))),
        "mean_bias_predicted_minus_observed": float(np.mean(predicted - actual)),
        "median_absolute_error": float(np.median(absolute_error)),
        "mean_absolute_percentage_error_nonzero_actual_pct": (
            float(np.mean(absolute_error[nonzero] / actual[nonzero]) * 100)
            if nonzero.any() else None
        ),
        "weighted_absolute_percentage_error_pct": (
            float(absolute_error.sum() / total_actual * 100)
            if total_actual > 0 else None
        ),
        "aggregate_prediction_to_observation_ratio": (
            float(predicted.sum() / total_actual) if total_actual > 0 else None
        ),
        "r2": float(r2_score(actual, predicted)) if len(actual) >= 2 else None,
        "event_level_mae": {
            str(event): float(np.mean(group["predicted_value"] - group["outcome_value"]).__abs__())
            for event, group in data.groupby("event_id", sort=True)
        },
    }
    return {
        "schema_version": "observed-impact-holdout-evaluation/1.0.0",
        "status": "HOLDOUT_EVALUATED_NOT_VALIDATION_CERTIFIED",
        "model_id": str(metadata["model_id"]),
        "model_version": str(metadata["model_version"]),
        "outcome_name": str(data["outcome_name"].iloc[0]),
        "outcome_unit": str(data["outcome_unit"].iloc[0]),
        "row_count": int(len(data)),
        "holdout_event_count": int(len(holdout_events)),
        "holdout_geography_count": int(len(holdout_geographies)),
        "training_holdout_event_overlap": [],
        "training_holdout_geography_overlap": [],
        "metrics": metrics,
        "evaluation_performed": True,
        "model_validated": False,
        "limitations": [
            "A passed holdout separation check does not prove the source observations are complete or unbiased.",
            "This evaluation does not establish causal intervention effects.",
            "Operational validation requires independent replication, calibration review and domain-expert approval.",
            "Exposed population, affected population, displaced population and casualties are distinct outcomes.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--holdout", required=True, help="Observed, source-linked holdout CSV.")
    parser.add_argument("--metadata", required=True, help="Model and split provenance JSON.")
    parser.add_argument("--output", default="reports/observed_impact_holdout_evaluation.json")
    args = parser.parse_args()
    frame = pd.read_csv(args.holdout)
    metadata = json.loads(Path(args.metadata).read_text(encoding="utf-8"))
    result = evaluate_observed_impact_holdout(frame, metadata)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps({
        "report": str(output),
        "status": result["status"],
        "evaluation_performed": result.get("evaluation_performed", False),
        "model_validated": result.get("model_validated", False),
    }, indent=2))
    return 0 if result.get("evaluation_performed") else 2


if __name__ == "__main__":
    raise SystemExit(main())
