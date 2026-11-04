import numpy as np
import pytest

from src.air_background_model import AirBackgroundModelError, make_features, predict_next_hour


class StubModel:
    def predict(self, frame):
        assert len(frame) == 1
        return np.array([18.5])


@pytest.fixture
def bundle():
    locations = ["Eloor_I", "Eloor_II", "Kochi"]
    features = [
        "pm2_5_ug_m3", "pm10_ug_m3", "no2_ug_m3", "so2_ug_m3", "co_ug_m3", "o3_ug_m3",
        "temperature_c", "relative_humidity_pct", "wind_speed_kmh", "wind_direction_sin",
        "wind_direction_cos", "hour_sin", "hour_cos", *[f"location_{name}" for name in locations],
    ]
    return {"model": StubModel(), "features": features, "locations": locations}


def valid_values():
    return {
        "location": "Eloor_I", "pm2_5_ug_m3": 12, "pm10_ug_m3": 25, "no2_ug_m3": 8,
        "so2_ug_m3": 2, "co_ug_m3": 190, "o3_ug_m3": 40, "temperature_c": 29,
        "relative_humidity_pct": 72, "wind_speed_kmh": 8, "wind_direction_deg": 180,
    }


def test_valid_inputs_produce_background_prediction(bundle):
    assert predict_next_hour(bundle, valid_values()) == 18.5


def test_missing_input_is_rejected_without_prediction(bundle):
    values = valid_values()
    values.pop("wind_speed_kmh")
    with pytest.raises(AirBackgroundModelError, match="wind_speed_kmh"):
        predict_next_hour(bundle, values)


def test_uncovered_location_is_rejected(bundle):
    values = valid_values()
    values["location"] = "Aluva"
    with pytest.raises(AirBackgroundModelError, match="not covered"):
        make_features(bundle, values)
