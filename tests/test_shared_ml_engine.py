"""Tests for the shared ML engine's scientific and deployment boundaries."""

from __future__ import annotations

import pandas as pd
import pytest

from src.hazard_registry import WORKFLOW_HAZARDS
from src.ml.coverage import build_coverage_matrix
from src.ml.evaluation import grade_skill, two_by_two_association
from src.ml.features import LeakageError, assert_no_leakage
from src.ml.inference import InferenceInputError, predict_from_context
from src.ml.registry import card_consistency_problems, list_model_cards, load_model_card
from src.ml.service import ml_evidence_for
from src.ml.training import temporal_split


def test_leakage_guard_rejects_target_and_future_features():
    with pytest.raises(LeakageError):
        assert_no_leakage(["rainfall", "target_flood"], "target_flood")
    with pytest.raises(LeakageError):
        assert_no_leakage(["rainfall", "future_river_level"], "flood")
    with pytest.raises(LeakageError):
        assert_no_leakage(["rainfall", "rainfall"], "flood")


def test_temporal_split_is_ordered_and_purges_crossing_groups():
    frame = pd.DataFrame(
        {
            "target_date": pd.to_datetime(
                [
                    "2020-01-01", "2020-01-02", "2020-01-03",  # A
                    "2020-01-04", "2020-01-05", "2020-01-06", "2020-01-07",  # B
                    "2020-01-08", "2020-01-09", "2020-01-10",  # C
                    "2020-01-03", "2020-01-04", "2020-01-05",  # D crosses train/validation
                ]
            ),
            "storm_id": ["A"] * 3 + ["B"] * 4 + ["C"] * 3 + ["D"] * 3,
        }
    )
    train, validation, test, purge = temporal_split(
        frame,
        date_column="target_date",
        validation_start=pd.Timestamp("2020-01-04"),
        test_start=pd.Timestamp("2020-01-08"),
        group_column="storm_id",
    )
    assert train["target_date"].max() < pd.Timestamp("2020-01-04")
    assert validation["target_date"].max() < pd.Timestamp("2020-01-08")
    assert set(train["storm_id"]).isdisjoint(set(validation["storm_id"]))
    assert set(train["storm_id"]).isdisjoint(set(test["storm_id"]))
    assert set(validation["storm_id"]).isdisjoint(set(test["storm_id"]))
    assert "D" not in set(train["storm_id"])
    assert purge["group_column"] == "storm_id"


def test_coverage_contains_exactly_the_ten_authoritative_hazards():
    coverage = build_coverage_matrix(write=False)
    assert coverage["coverage_complete"] is True
    assert coverage["n_hazards"] == 10
    assert [entry["hazard"] for entry in coverage["entries"]] == list(WORKFLOW_HAZARDS)
    assert coverage["hazards_without_ml_evidence"] == [
        "Landslide",
        "Industrial incident",
        "Infrastructure failure",
    ]
    assert coverage["validated_models"] == 0


def test_no_model_hazard_returns_an_explicit_no_model_evidence_block():
    evidence = ml_evidence_for("Landslide", {})
    assert evidence["status"] == "no_model_available"
    assert evidence["models"] == []
    assert evidence["validated_prediction_available"] is False
    assert "supervised landslide model" in evidence["interpretation"].lower()


def test_inference_without_complete_context_fails_closed():
    if load_model_card("weather_high_temperature_kochi_nextday") is not None:
        with pytest.raises(InferenceInputError):
            predict_from_context("weather_high_temperature_kochi_nextday", {})
    evidence = ml_evidence_for("Heatwave", {})
    assert evidence["status"] in {"available_context_incomplete", "not_trained"}
    assert evidence["applications"] == []
    assert evidence["validated_prediction_available"] is False


def test_ml_evidence_rejects_an_unknown_hazard_label():
    with pytest.raises(ValueError):
        ml_evidence_for("Wildfire", {})


def test_skill_grade_downgrades_when_probability_error_is_worse_than_base_rate():
    result = grade_skill(
        {
            "n_test_events": 40,
            "test_prevalence": 0.07,
            "roc_auc": 0.86,
            "average_precision": 0.36,
            "brier_score": 0.09,
            "base_rate_brier_score": 0.065,
            "expected_calibration_error": 0.14,
        }
    )
    assert result["status"] == "WEAK_RESEARCH_SIGNAL"
    assert "base-rate reference" in result["reason"]


def test_two_by_two_association_reports_raw_counts_and_haldane_odds_ratio():
    result = two_by_two_association([1, 1, 0, 0], [1, 0, 1, 0], exposure_name="near")
    assert result["table"] == {
        "exposed_event": 1,
        "exposed_no_event": 1,
        "unexposed_event": 1,
        "unexposed_no_event": 1,
    }
    assert result["odds_ratio_haldane_corrected"] == pytest.approx(1.0)
    assert "not a causal" in result["interpretation"] or "association only" in result["interpretation"]


@pytest.mark.skipif(not list_model_cards(), reason="Shared ML artifacts are not present in this checkout.")
def test_every_registered_card_is_consistent_and_makes_no_validation_claim():
    cards = list_model_cards()
    assert cards
    for card in cards:
        assert card_consistency_problems(card) == []
        assert card["validation_status"] == "SINGLE_TEMPORAL_HOLDOUT_NOT_INDEPENDENTLY_VALIDATED"
        assert card["status"] != "VALIDATED"
        assert card["metrics"]["n_test"] > 0


@pytest.mark.skipif(not list_model_cards(), reason="Shared ML artifacts are not present in this checkout.")
def test_compound_card_is_explicitly_exploratory_and_reports_an_ablation():
    card = load_model_card("compound_cyclone_rainfall_interaction")
    if card is None:
        pytest.skip("Compound association card is not present.")
    assert card["evidence_tier"] == "exploratory_association"
    assert card["status"] == "EXPLORATORY_ASSOCIATION"
    assert "no forecast lead time" in card["status_reason"].lower()
    ablation = card["metrics"].get("ablation")
    assert isinstance(ablation, dict) and ablation.get("available") is True
    assert ablation["excluded_columns"]
    association = card["metrics"].get("association_analysis")
    assert isinstance(association, dict)
    assert "final_train" in association and "test" in association


def test_flood_assessment_still_renders_without_ml_context():
    from src.disaster_models import assess_disaster

    assessment = assess_disaster(
        {"hazard": "Flood", "input_classification": "Unknown / unverified"}
    )
    assert assessment["disaster"] == "Flood"
    evidence = assessment["ml_evidence"]
    assert evidence["hazard"] == "Flood"
    assert evidence["validated_prediction_available"] is False
    assert evidence["status"] in {
        "available_context_incomplete",
        "available_not_applied",
        "not_trained",
        "no_model_available",
    }


def test_compound_workspace_assessment_accepts_all_ten_registered_hazards():
    from src.compound_hazard_assessment import assess_compound_scenario

    for hazard in WORKFLOW_HAZARDS:
        result = assess_compound_scenario({"area": "Kochi", "hazards": [hazard]})
        assert hazard in result["hazards"]
        assert result["pathways"]
        assert result["numerical_probability_provided"] is False


def test_compound_workspace_custom_disaster_is_qualitative_and_unregistered():
    from src.compound_hazard_assessment import assess_compound_scenario

    result = assess_compound_scenario({
        "area": "Kochi", "hazards": [], "custom_disaster": "Custom test scenario"
    })
    assert result["custom_disaster"] == "Custom test scenario"
    assert any(item["hazard"] == "Custom disaster (unregistered)" for item in result["pathways"])
    assert result["numerical_probability_provided"] is False


def test_compound_registry_label_expands_to_component_evidence_requirements():
    from src.compound_hazard_assessment import assess_compound_scenario

    result = assess_compound_scenario({
        "area": "Kochi", "hazards": ["Compound: cyclone + flood"]
    })
    assert any("rainfall observation" in gap.lower() for gap in result["data_gaps"])
    assert any("cyclone track position" in gap.lower() for gap in result["data_gaps"])
