"""Regression tests for next-day weather research-model feature timing and threshold isolation."""
import pandas as pd

from scripts.train_weather_hazard_baselines import (
    feature_columns,
    make_features,
    training_event_threshold,
)


def test_next_day_features_include_current_day_observations_without_target_leakage():
    dates = pd.date_range("2020-01-01", periods=12, freq="D")
    frame = pd.DataFrame({
        "date": dates,
        "location": ["kochi"] * len(dates),
        "temperature_2m_max": list(range(20, 32)),
        "temperature_2m_min": list(range(10, 22)),
        "precipitation_sum": list(range(12)),
        "wind_speed_10m_max": list(range(5, 17)),
        "wind_gusts_10m_max": list(range(8, 20)),
    })
    featured = make_features(frame)
    predictors = feature_columns(featured)
    row = featured.loc[featured["date"] == pd.Timestamp("2020-01-06")].iloc[0]

    assert "temperature_2m_max" in predictors
    assert row["temperature_2m_max"] == 25
    assert row["target_temperature_nextday"] == 26
    assert "target_temperature_nextday" not in predictors
    assert "target_rain_nextday" not in predictors


def test_event_threshold_uses_only_pre_validation_target_dates():
    dates = list(pd.date_range("2014-01-01", periods=120, freq="D"))
    dates += list(pd.date_range("2015-01-01", periods=120, freq="D"))
    frame = pd.DataFrame({
        "target_date": dates,
        "target_nextday": [1.0] * 120 + [1000.0] * 120,
    })

    threshold = training_event_threshold(frame, "target_nextday", "2015-01-01")

    assert threshold == 1.0


def test_event_threshold_refuses_too_few_training_outcomes():
    frame = pd.DataFrame({
        "target_date": pd.date_range("2014-01-01", periods=99, freq="D"),
        "target_nextday": [float(i) for i in range(99)],
    })

    try:
        training_event_threshold(frame, "target_nextday", "2015-01-01")
    except RuntimeError as exc:
        assert "Insufficient pre-validation training outcomes" in str(exc)
    else:
        raise AssertionError("Expected a clear refusal for insufficient training data.")
