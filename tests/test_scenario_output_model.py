"""Tests for the ten-hazard conditional scenario output engine."""
import pytest

from src.scenario_output_model import HAZARDS, predict_scenario_outcome


@pytest.mark.parametrize("hazard", HAZARDS)
def test_every_workflow_hazard_returns_a_structured_output(hazard):
    result = predict_scenario_outcome({"hazard": hazard})
    assert result["hazard"] == hazard
    assert result["conditional_outcome"]
    assert result["concern_level"]
    assert result["numerical_probability"] is None
    assert result["is_trained_ml"] is False
    assert result["is_official_warning"] is False


def test_flood_with_impaired_drainage_returns_conditional_waterlogging_outcome():
    result = predict_scenario_outcome({
        "hazard": "Flood",
        "rainfall_mm": 90,
        "rainfall_period": "Last 24 hours",
        "drainage_status": "Reported failed",
    })
    assert result["concern_level"] == "Elevated conditional waterlogging concern"
    assert "plausible" in result["conditional_outcome"]


def test_compound_rainfall_and_drainage_requires_both_inputs():
    incomplete = predict_scenario_outcome({
        "hazard": "Compound: heavy rainfall + drainage failure",
        "rainfall_mm": 100,
        "rainfall_period": "Last 24 hours",
    })
    complete = predict_scenario_outcome({
        "hazard": "Compound: heavy rainfall + drainage failure",
        "rainfall_mm": 100,
        "rainfall_period": "Last 24 hours",
        "drainage_status": "Reported failed",
    })
    assert incomplete["concern_level"] == "Compound scenario incompletely specified"
    assert complete["concern_level"] == "Elevated conditional waterlogging concern"


def test_heatwave_does_not_claim_official_classification_from_temperature():
    result = predict_scenario_outcome({"hazard": "Heatwave", "temperature_c": 39})
    assert "cannot establish a heatwave" in result["conditional_outcome"]


def test_industrial_incident_never_invents_a_safe_distance():
    result = predict_scenario_outcome({
        "hazard": "Industrial incident",
        "industrial_substance": "unknown",
        "industrial_release_status": "Confirmed by cited authority",
    })
    assert "safe distance" in result["conditional_outcome"]
    assert result["numerical_probability"] is None


def test_unsupported_hazard_is_rejected():
    with pytest.raises(ValueError):
        predict_scenario_outcome({"hazard": "volcano"})
