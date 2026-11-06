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
        if card.get("evaluation_validity") == "INVALIDATED_TARGET_CONSTRUCTION":
            assert card["status"] == "NO_SKILL"
            assert card["metrics"] == {}
            assert "invalidated" in card["status_reason"].lower()
        else:
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


def test_temporal_split_purges_labels_whose_future_windows_cross_boundaries():
    from src.ml.training import temporal_split

    frame = pd.DataFrame({
        "target_date": pd.to_datetime([
            "2017-12-20", "2017-12-28", "2018-01-02",
            "2021-12-20", "2021-12-28", "2022-01-02",
        ]),
        "target_window_end": pd.to_datetime([
            "2017-12-27", "2018-01-04", "2018-01-09",
            "2021-12-27", "2022-01-04", "2022-01-09",
        ]),
        "row": list(range(6)),
    })
    train, validation, test, purge = temporal_split(
        frame,
        date_column="target_date",
        validation_start=pd.Timestamp("2018-01-01"),
        test_start=pd.Timestamp("2022-01-01"),
        label_end_column="target_window_end",
    )
    assert train["row"].tolist() == [0]
    assert validation["row"].tolist() == [2, 3]
    assert test["row"].tolist() == [5]
    assert purge["purged_train_label_window_rows"] == 1
    assert purge["purged_validation_label_window_rows"] == 1
    assert purge["purged_label_window_rows"] == 2


def test_skill_grade_downgrades_when_model_does_not_beat_persistence():
    result = grade_skill({
        "n_test_events": 40,
        "test_prevalence": 0.20,
        "roc_auc": 0.82,
        "average_precision": 0.55,
        "brier_score": 0.10,
        "base_rate_brier_score": 0.16,
        "f1": 0.60,
        "persistence_baseline": {"available": True, "f1": 0.70},
    })
    assert result["status"] == "WEAK_RESEARCH_SIGNAL"
    assert "does not exceed the persistence baseline" in result["reason"]


def test_forward_window_sum_uses_only_future_observations():
    from src.ml.data import _forward_window_sum

    values = pd.Series(range(1, 41), dtype=float)
    future = _forward_window_sum(values, 30)
    assert future.iloc[0] == pytest.approx(sum(range(2, 32)))
    assert future.iloc[5] == pytest.approx(sum(range(7, 37)))
    assert pd.isna(future.iloc[10])


def test_forward_window_sum_rejects_non_positive_window():
    from src.ml.data import _forward_window_sum

    with pytest.raises(ValueError, match="at least one"):
        _forward_window_sum(pd.Series([1.0, 2.0]), 0)


def test_coverage_distinguishes_registered_artifacts_from_usable_models():
    coverage = build_coverage_matrix(write=False)
    drought = next(item for item in coverage["entries"] if item["hazard"] == "Drought")
    assert drought["model_statuses"]["weather_drought_onset_kochi_30day"] == "NO_SKILL"
    assert drought["support_level"] == "no_skill_model"
    assert "Drought" in coverage["hazards_without_usable_research_model"]
    assert coverage["n_hazards_with_usable_research_model"] == 2
    assert coverage["hazards_with_usable_research_model"] == ["Cyclone", "Heatwave"]
    assert coverage["n_hazards_with_component_research_evidence"] >= 2


def test_invalidated_drought_model_is_blocked_from_inference():
    from src.ml.inference import ModelNotUsableError, predict_from_context

    with pytest.raises(ModelNotUsableError, match="invalidated evaluation provenance"):
        predict_from_context("weather_drought_onset_kochi_30day", {}, allow_no_skill=True)


def test_invalidated_earthquake_model_is_blocked_from_inference():
    from src.ml.inference import ModelNotUsableError, predict_from_context

    with pytest.raises(ModelNotUsableError, match="invalidated evaluation provenance"):
        predict_from_context("earthquake_aftershock_occurrence", {}, allow_no_skill=True)


def test_regression_metrics_match_known_values():
    import numpy as np
    from src.ml.regression import _regression_metrics
    metrics = _regression_metrics(np.asarray([1.0, 2.0, 3.0]), np.asarray([1.0, 2.0, 4.0]))
    assert metrics["mae"] == pytest.approx(1.0 / 3.0)
    assert metrics["rmse"] == pytest.approx((1.0 / 3.0) ** 0.5)
    assert metrics["n"] == 3


def test_regression_inference_rejects_classification_model():
    from src.ml.inference import ModelNotUsableError, predict_regression_from_context
    with pytest.raises(ModelNotUsableError, match="not a registered regression model"):
        predict_regression_from_context("weather_extreme_rainfall_kochi_nextday", {})



def test_presentation_rows_distinguish_regression_from_probability():
    from src.ml.presentation import application_rows, card_rows

    application = {
        "model_id": "weather_tmax_kochi_nextday_regression",
        "task_type": "regression",
        "estimate": 31.2,
        "unit": "degrees Celsius",
        "target_definition": "Next-day maximum temperature",
    }
    row = application_rows({"applications": [application]})[0]
    assert row["Task"] == "Regression"
    assert row["Continuous estimate"] == 31.2
    assert row["Model probability estimate"] is None
    card = card_rows([{
        "model_id": "weather_tmax_kochi_nextday_regression",
        "task_type": "regression",
        "metrics": {"mae": 1.2, "rmse": 1.6, "mae_skill_over_persistence": 0.1},
    }])[0]
    assert card["Task"] == "regression"
    assert card["MAE"] == 1.2



def test_continuous_models_are_registered_in_shared_hazard_coverage():
    coverage = build_coverage_matrix(write=False)
    by_hazard = {entry["hazard"]: entry for entry in coverage["entries"]}
    assert "weather_precipitation_kochi_nextday_regression" in by_hazard["Flood"]["model_ids"]
    assert "weather_tmax_kochi_nextday_regression" in by_hazard["Heatwave"]["model_ids"]
    assert "cyclone_wind_change_24h_regression" in by_hazard["Cyclone"]["model_ids"]



def test_regression_paired_bootstrap_requires_baseline_improvement():
    import numpy as np
    from src.ml.regression import _paired_mae_improvement_ci

    actual = np.asarray([0.0, 1.0, 2.0, 3.0] * 20)
    good = np.asarray([0.0, 1.0, 2.0, 3.0] * 20)
    bad_baseline = good + 1.0
    low, high = _paired_mae_improvement_ci(actual, good, bad_baseline)
    assert low > 0
    assert high > low



def test_regression_training_uses_temporal_holdout_and_baseline(monkeypatch):
    import numpy as np
    from src.ml.data import Dataset
    import src.ml.regression as regression

    rng = np.random.default_rng(7)
    dates = pd.date_range("2010-01-01", "2025-12-31", freq="D")
    x = rng.normal(size=len(dates))
    target = 2.5 * x + rng.normal(scale=0.15, size=len(dates))
    frame = pd.DataFrame({
        "target_date": dates,
        "feature_x": x,
        "target_value": target,
        "naive_baseline": np.zeros(len(dates)),
    })
    dataset = Dataset(
        name="synthetic_unit_test_only",
        frame=frame,
        target_column="target_value",
        date_column="target_date",
        feature_columns=["feature_x"],
    )
    monkeypatch.setattr(regression, "REGRESSION_CANDIDATES", ("ridge_regressor",))
    monkeypatch.setattr(regression, "save_model_bundle", lambda *args, **kwargs: {})
    card = regression.train_regression_dataset(
        dataset,
        model_id="unit_test_regression",
        hazard="Test",
        persistence_column="naive_baseline",
        unit="test units",
    )
    assert card["task_type"] == "regression"
    assert card["temporal_split"]["test_rows"] > 100
    assert card["metrics"]["mae"] < card["metrics"]["persistence_baseline"]["mae"]
    assert card["metrics"]["paired_mae_improvement_bootstrap_95ci"][0] > 0
    assert card["status"] == "WEAK_RESEARCH_SIGNAL"
