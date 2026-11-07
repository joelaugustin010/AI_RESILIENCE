"""Tests for independent observed-impact holdout evaluation."""
import pandas as pd

from scripts.evaluate_observed_impact_holdout import evaluate_observed_impact_holdout


def _metadata():
    return {
        "model_id": "impact-screening-test",
        "model_version": "0.1",
        "outcome_definition": "affected_people",
        "outcome_unit": "persons",
        "training_event_ids": ["train-event-1", "train-event-2"],
        "training_geographies": ["train-ward-a", "train-ward-b"],
        "ground_truth_source": "official event records",
        "prediction_method": "held-out model predictions",
        "known_limitations": ["test fixture only"],
    }


def _frame():
    return pd.DataFrame([
        {
            "observation_id": f"obs-{event}-{ward}",
            "event_id": event,
            "geography_id": ward,
            "observation_date": "2025-08-01",
            "outcome_name": "affected_people",
            "outcome_value": actual,
            "predicted_value": predicted,
            "outcome_unit": "persons",
            "source_url": "https://example.org/official-record",
        }
        for event, values in {
            "holdout-event-1": [("ward-a", 100, 110), ("ward-b", 50, 45)],
            "holdout-event-2": [("ward-a", 80, 90), ("ward-b", 40, 40)],
            "holdout-event-3": [("ward-a", 60, 55), ("ward-b", 30, 35)],
        }.items()
        for ward, actual, predicted in values
    ])


def test_independent_observed_impact_holdout_is_scored_but_not_certified():
    result = evaluate_observed_impact_holdout(_frame(), _metadata())
    assert result["status"] == "HOLDOUT_EVALUATED_NOT_VALIDATION_CERTIFIED"
    assert result["evaluation_performed"] is True
    assert result["model_validated"] is False
    assert result["holdout_event_count"] == 3
    assert result["holdout_geography_count"] == 2
    assert result["metrics"]["mae"] == 6.666666666666667
    assert result["metrics"]["event_level_mae"]["holdout-event-1"] == 7.5


def test_training_event_overlap_blocks_impact_evaluation():
    metadata = _metadata()
    metadata["training_event_ids"].append("holdout-event-1")
    result = evaluate_observed_impact_holdout(_frame(), metadata)
    assert result["status"] == "BLOCKED_DATA_OR_INDEPENDENCE_GAPS"
    assert result["evaluation_performed"] is False
    assert result["model_validated"] is False
    assert any("event leakage" in item for item in result["problems"])


def test_missing_training_split_metadata_is_blocked_without_crashing():
    metadata = _metadata()
    metadata["training_event_ids"] = None
    result = evaluate_observed_impact_holdout(_frame(), metadata)
    assert result["status"] == "BLOCKED_DATA_OR_INDEPENDENCE_GAPS"
    assert any("training event IDs" in item for item in result["problems"])
