import json

import pytest

from src.air_background_model import EVALUATION_PATH, make_features, predict_next_hour


def _values():
    return {
        "pm2_5_ug_m3": 32.4, "pm10_ug_m3": 54.0, "no2_ug_m3": 12.0,
        "so2_ug_m3": 4.0, "co_ug_m3": 220.0, "o3_ug_m3": 80.0,
        "temperature_c": 28.0, "relative_humidity_pct": 75.0,
        "wind_speed_kmh": 8.0, "wind_direction_deg": 180.0, "hour": 12,
    }


def test_evaluation_artifact_declares_background_boundary():
    report = json.loads(EVALUATION_PATH.read_text(encoding="utf-8"))
    assert "not a disaster-plume predictor" in report["scientific_boundary"]
    assert report["locations"] == ["Eloor_I", "Eloor_II", "Kochi"]


def test_make_features_matches_evaluated_schema():
    features = [
        "pm2_5_ug_m3", "pm10_ug_m3", "no2_ug_m3", "so2_ug_m3", "co_ug_m3", "o3_ug_m3",
        "temperature_c", "relative_humidity_pct", "wind_speed_kmh", "wind_direction_sin",
        "wind_direction_cos", "hour_sin", "hour_cos", "location_Kochi",
    ]
    frame = make_features(_values(), "Kochi", features=features)
    assert list(frame.columns) == features
    assert frame.loc[0, "location_Kochi"] == 1.0


def test_predict_next_hour_returns_nonnegative_value():
    assert predict_next_hour(_values(), "Kochi") >= 0


def test_predict_rejects_unknown_location():
    with pytest.raises(Exception, match="not covered"):
        predict_next_hour(_values(), "Edayar")
