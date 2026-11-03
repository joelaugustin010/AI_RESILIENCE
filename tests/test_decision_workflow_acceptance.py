"""Acceptance gates for the unified disaster decision workflow.

These tests verify consistent scenario plumbing and conservative decision behavior.
They do not claim that the workflow is a validated disaster predictor.
"""
from pathlib import Path

import pytest

from src.decision_workflow import (
    HAZARD_OPTIONS,
    assessment_summary,
    build_scenario_comparison,
    budget_summary,
    compare_action_combinations,
    decision_readiness_summary,
    evidence_provenance_summary,
    expand_hazards,
    hazard_evidence_checklist,
    mitigation_actions_for,
    validate_workflow_inputs,
)
from src.scenario_input_quality import evaluate_scenario_readiness


ROOT = Path(__file__).resolve().parents[1]


def sample_inputs(hazard: str) -> dict:
    return {
        "hazard": hazard,
        "location": "Kochi — illustrative area only",
        "input_classification": "Hypothetical scenario assumption",
        "source_and_time": "",
        "rainfall_mm": None,
        "rainfall_period": "Not supplied",
        "river_level_m": None,
        "wind_speed_kmh": None,
        "temperature_c": None,
        "affected_population": None,
        "assets": ["Hospital access", "Road access"],
    }


@pytest.mark.parametrize("hazard", HAZARD_OPTIONS)
def test_every_hazard_completes_the_same_decision_pipeline(hazard):
    inputs = sample_inputs(hazard)
    quality = evaluate_scenario_readiness(hazard, inputs)
    scenarios = build_scenario_comparison(inputs)
    actions = mitigation_actions_for(hazard)
    checklist = hazard_evidence_checklist(inputs, ROOT)
    readiness = decision_readiness_summary(inputs, quality)
    summary = assessment_summary(inputs)

    assert len(scenarios) == 3
    assert {"Scenario", "Classification", "Assumptions", "Possible consequences to review"}.issubset(scenarios.columns)
    assert not actions.empty
    assert {"Action", "Hazard", "Prerequisite / evidence needed", "Cost INR"}.issubset(actions.columns)
    assert not checklist.empty
    assert {"Evidence needed", "Known limitation", "Next verification step"}.issubset(checklist.columns)
    assert readiness["numerical_prediction_gate"].startswith("CLOSED")
    assert "not validated" in summary["status"].lower()
    assert "probability" in summary["method"].lower()


@pytest.mark.parametrize(
    ("selection", "expected"),
    [
        ("Compound: cyclone + flood", {"Cyclone", "Flood"}),
        ("Compound: heavy rainfall + drainage failure", {"Flood", "Infrastructure failure"}),
    ],
)
def test_compound_hazards_preserve_both_components(selection, expected):
    assert set(expand_hazards(selection)) == expected
    checklist = hazard_evidence_checklist(sample_inputs(selection), ROOT)
    assert set(checklist["Hazard component"]) == expected


def test_invalid_numeric_input_and_missing_rainfall_period_are_blocked():
    problems = validate_workflow_inputs({
        "hazard": "Flood",
        "location": "Kochi",
        "rainfall_mm": float("nan"),
        "rainfall_period": "Not supplied",
    })
    assert any("finite" in problem.lower() for problem in problems)
    assert any("time period" in problem.lower() for problem in problems)


def test_budget_does_not_claim_fit_when_any_cost_is_unknown():
    result = budget_summary([1000, None], 5000)
    assert result["entered_total"] == 1000
    assert result["unknown_or_invalid_count"] == 1
    assert result["within_budget"] is None


def test_action_comparison_fails_closed_for_unknown_action_names():
    actions = mitigation_actions_for("Flood").head(1).copy()
    result = compare_action_combinations(
        actions,
        100000,
        {"Typo / stale selection": ["action that does not exist"]},
    )
    row = result.iloc[0]
    assert "Cannot confirm fit" in row["Budget status"]
    assert "Unknown action" in row["Selection issues"]


def test_hypothetical_inputs_never_open_prediction_gate_even_if_form_is_complete():
    inputs = sample_inputs("Flood")
    inputs.update({
        "source_and_time": "Example source, illustrative timestamp",
        "rainfall_mm": 40,
        "rainfall_period": "Last 24 hours",
        "river_level_m": 2.0,
        "river_station": "Example station",
        "river_reference": "Example datum",
        "drainage_status": "Reported functioning",
    })
    quality = evaluate_scenario_readiness("Flood", inputs)
    readiness = decision_readiness_summary(inputs, quality)
    assert quality["numerical_prediction_enabled"] is False
    assert readiness["numerical_prediction_gate"].startswith("CLOSED")
    assert "WHAT-IF PLANNING ONLY" in readiness["decision_status"]


def test_historical_event_classification_is_shared_and_remains_unverified():
    from src.decision_workflow import INPUT_CLASSIFICATIONS
    from src.disaster_models.common import INPUT_CLASSIFICATIONS as MODEL_CLASSIFICATIONS

    classification = "Historical event (source not independently verified)"
    assert classification in INPUT_CLASSIFICATIONS
    assert classification in MODEL_CLASSIFICATIONS
    provenance = evidence_provenance_summary({"input_classification": classification})
    assert "historical event" in provenance["Provenance status"].lower()
    assert "not independently verified" in provenance["Provenance status"].lower()
    assert "current conditions" in provenance["Permitted interpretation"]
