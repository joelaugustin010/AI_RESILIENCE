from types import SimpleNamespace

import pandas as pd
import pytest

from src.ml import service


def _card():
    return {
        "model_id": "weather_precipitation_kochi_nextday_regression",
        "dataset_name": "weather_extreme_rainfall_kochi",
        "target_column": "target_rain_nextday",
        "target_definition": "Next-day precipitation in mm/day.",
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
            "target_date": pd.to_datetime(["2019-12-31", "2020-01-01", "2020-01-02"], utc=True),
            "target_rain_nextday": [1.0, 8.0, 12.0],
            "rain_lag1": [2.0, 3.0, 4.0],
            "temperature": [28.0, 29.0, 30.0],
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
