from types import SimpleNamespace

import pandas as pd
import pytest

"""Geographic scope guards for location-specific disaster research models."""

from src.ml import service
from src.ml.service import _geographic_scope_problem


def _kochi_card():
    return {"provenance": {"location": "kochi"}}


def test_kochi_weather_model_accepts_explicit_kochi_location():
    assert _geographic_scope_problem(
        _kochi_card(),
        {"location": "Kochi Municipal Corporation — area not specified"},
    ) is None


def test_kochi_weather_model_rejects_other_city():
    problem = _geographic_scope_problem(
        _kochi_card(), {"location": "Thiruvananthapuram, Kerala"}
    )

    assert problem is not None
    assert "cannot be applied" in problem


def test_kochi_weather_model_requires_explicit_location():
    problem = _geographic_scope_problem(_kochi_card(), {"rainfall_mm": 100})

    assert problem is not None
    assert "explicit location is required" in problem


def test_non_local_model_without_location_scope_is_not_restricted():
    card = {"provenance": {"source": "IBTrACS North Indian Ocean"}}

    assert _geographic_scope_problem(card, {}) is None



def test_ml_evidence_can_be_restricted_to_selected_registered_model(monkeypatch):
    monkeypatch.setattr(service, "WORKFLOW_HAZARDS", {"Test Hazard"})
    monkeypatch.setattr(
        service,
        "coverage_entry",
        lambda hazard: {
            "model_ids": ["model-a", "model-b"],
            "support_level": "research",
            "interpretation": "research only",
            "limitations": [],
        },
    )
    called = []

    def fake_model_entry(model_id, inputs):
        called.append(model_id)
        return (
            {
                "model_id": model_id,
                "status": "WEAK_RESEARCH_SIGNAL",
                "context": {"missing_features": []},
            },
            None,
        )

    monkeypatch.setattr(service, "_model_entry", fake_model_entry)
    monkeypatch.setattr(service, "load_model_card", lambda model_id: None)

    result = service.ml_evidence_for(
        "Test Hazard",
        {"ml_context": {"feature": 1}},
        selected_model_id="model-b",
    )

    assert called == ["model-b"]
    assert [row["model_id"] for row in result["models"]] == ["model-b"]


def test_ml_evidence_rejects_model_not_registered_for_selected_hazard(monkeypatch):
    monkeypatch.setattr(service, "WORKFLOW_HAZARDS", {"Test Hazard"})
    monkeypatch.setattr(
        service,
        "coverage_entry",
        lambda hazard: {
            "model_ids": ["model-a"],
            "support_level": "research",
            "interpretation": "research only",
            "limitations": [],
        },
    )

    try:
        service.ml_evidence_for(
            "Test Hazard",
            {},
            selected_model_id="model-outside-hazard",
        )
    except ValueError as error:
        assert "not registered for hazard" in str(error)
    else:
        raise AssertionError("An unregistered model must not be applied to a hazard.")



def _card():
    return {
        "model_id": "weather_precipitation_kochi_nextday_regression",
        "dataset_name": "weather_extreme_rainfall_kochi",
        "target_column": "target_rain_nextday",
        "target_definition": "Next-day precipitation in mm/day.",
        "task_type": "regression",
        "feature_columns": ["rain_lag1", "temperature"],
        "feature_ranges": {
            "rain_lag1": {"min": 0.0, "max": 3.0},
            "temperature": {"min": 20.0, "max": 35.0},
        },
        "temporal_split": {"test_start": "2020-01-01"},
        "provenance": {
            "target": "extreme_rainfall",
            "location": "kochi",
            "source_type": "MODELLED_REANALYSIS_GRID_POINT_NOT_STATION_OBSERVATION",
        },
    }


def _dataset():
    frame = pd.DataFrame(
        {
            "target_date": pd.to_datetime(["2019-12-31", "2020-01-01", "2020-01-02", "2020-01-03"], utc=True),
            "target_rain_nextday": [1.0, 8.0, 12.0, 15.0],
            "rain_lag1": [2.0, 3.0, 4.0, 2.5],
            "temperature": [28.0, 29.0, 30.0, float("inf")],
        }
    )
    return SimpleNamespace(
        frame=frame,
        date_column="target_date",
        target_column="target_rain_nextday",
        provenance={"source": "test weather fixture"},
    )


def test_historical_replay_uses_latest_complete_test_row_and_excludes_target(monkeypatch):
    monkeypatch.setattr(service, "load_model_card", lambda model_id: _card())
    monkeypatch.setattr(
        service,
        "build_weather_target_dataset",
        lambda location, target: _dataset(),
    )

    replay = service.historical_replay_context("weather_precipitation_kochi_nextday_regression")

    assert replay["case_date"] == "2020-01-01"
    assert replay["context"] == {"rain_lag1": 3.0, "temperature": 29.0}
    assert replay["observed_target"] == 8.0
    assert replay["observed_event"] is None
    assert "target_rain_nextday" not in replay["context"]
    assert replay["case_role"].startswith("latest complete in-domain row")


def test_historical_replay_rejects_missing_test_period_rows(monkeypatch):
    monkeypatch.setattr(service, "load_model_card", lambda model_id: _card())
    frame = _dataset().frame.iloc[:1].copy()
    dataset = SimpleNamespace(
        frame=frame,
        date_column="target_date",
        target_column="target_rain_nextday",
        provenance={},
    )
    monkeypatch.setattr(
        service,
        "build_weather_target_dataset",
        lambda location, target: dataset,
    )

    with pytest.raises(ValueError, match="No complete historical test-period row"):
        service.historical_replay_context("weather_precipitation_kochi_nextday_regression")


def test_historical_replay_rejects_unregistered_dataset_builder(monkeypatch):
    card = _card()
    card["dataset_name"] = "unregistered_dataset"
    monkeypatch.setattr(service, "load_model_card", lambda model_id: card)

    with pytest.raises(ValueError, match="No historical replay builder"):
        service.historical_replay_context("unknown-model")



def test_historical_replay_derives_observed_class_from_card_threshold(monkeypatch):
    card = _card()
    card.update({"task_type": "classification", "target_threshold": 10.0, "target_direction": "high"})
    monkeypatch.setattr(service, "load_model_card", lambda model_id: card)
    monkeypatch.setattr(
        service,
        "build_weather_target_dataset",
        lambda location, target: _dataset(),
    )

    replay = service.historical_replay_context("weather_precipitation_kochi_nextday_regression")

    assert replay["observed_target"] == 8.0
    assert replay["observed_event"] is False
