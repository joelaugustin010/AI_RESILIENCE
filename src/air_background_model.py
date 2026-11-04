"""Guarded inference for the trained CAMS/Open-Meteo background model."""

from __future__ import annotations

import math
import pickle
from pathlib import Path

import numpy as np
import pandas as pd


REQUIRED_BASE_FIELDS = (
    "pm2_5_ug_m3", "pm10_ug_m3", "no2_ug_m3", "so2_ug_m3", "co_ug_m3", "o3_ug_m3",
    "temperature_c", "relative_humidity_pct", "wind_speed_kmh", "wind_direction_deg",
    "location",
)


class AirBackgroundModelError(ValueError):
    """Raised when the background model cannot safely produce a prediction."""


def load_model(path: Path) -> dict:
    if not path.is_file():
        raise AirBackgroundModelError("The trained background model artifact is unavailable.")
    try:
        with path.open("rb") as stream:
            bundle = pickle.load(stream)
    except (OSError, pickle.UnpicklingError, EOFError) as error:
        raise AirBackgroundModelError("The trained background model artifact could not be loaded.") from error
    if not isinstance(bundle, dict) or not hasattr(bundle.get("model"), "predict"):
        raise AirBackgroundModelError("The trained background model artifact is invalid.")
    return bundle


def make_features(bundle: dict, values: dict[str, object]) -> pd.DataFrame:
    missing = [field for field in REQUIRED_BASE_FIELDS if field not in values or values[field] in (None, "")]
    if missing:
        raise AirBackgroundModelError(f"Missing model inputs: {', '.join(missing)}")
    numeric = {}
    for field in REQUIRED_BASE_FIELDS:
        if field == "location":
            continue
        try:
            parsed = float(values[field])
        except (TypeError, ValueError) as error:
            raise AirBackgroundModelError(f"Invalid numeric input: {field}") from error
        if not math.isfinite(parsed):
            raise AirBackgroundModelError(f"Invalid numeric input: {field}")
        numeric[field] = parsed
    if numeric["pm2_5_ug_m3"] < 0 or numeric["pm10_ug_m3"] < 0 or numeric["wind_speed_kmh"] < 0:
        raise AirBackgroundModelError("Concentrations and wind speed cannot be negative.")
    direction = numeric.pop("wind_direction_deg")
    numeric["wind_direction_sin"] = math.sin(math.radians(direction))
    numeric["wind_direction_cos"] = math.cos(math.radians(direction))
    numeric["hour_sin"] = 0.0
    numeric["hour_cos"] = 1.0
    location = str(values["location"])
    locations = bundle.get("locations", [])
    if location not in locations:
        raise AirBackgroundModelError("Location is not covered by the trained model.")
    for known_location in locations:
        numeric[f"location_{known_location}"] = 1.0 if known_location == location else 0.0
    features = bundle.get("features", [])
    if not features or any(feature not in numeric for feature in features):
        raise AirBackgroundModelError("The model feature schema is incomplete.")
    return pd.DataFrame([[numeric[feature] for feature in features]], columns=features)


def predict_next_hour(bundle: dict, values: dict[str, object]) -> float:
    features = make_features(bundle, values)
    prediction = float(np.asarray(bundle["model"].predict(features)).reshape(-1)[0])
    if not math.isfinite(prediction) or prediction < 0:
        raise AirBackgroundModelError("The model returned an invalid PM2.5 value.")
    return prediction
