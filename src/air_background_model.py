"""Inference helpers for the evaluated Kerala CAMS background PM2.5 model.

The model predicts the next hourly CAMS/Open-Meteo background value.  It is
not an incident, plume, station-observation, or facility-attribution model.
"""

from __future__ import annotations

import pickle
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "models" / "air_quality" / "kerala_cams_pm25_next_hour_background.pkl"
EVALUATION_PATH = ROOT / "models" / "air_quality" / "kerala_cams_pm25_next_hour_background.evaluation.json"


class BackgroundModelError(RuntimeError):
    """Raised when the background model cannot produce a safe prediction."""


@lru_cache(maxsize=1)
def load_background_model() -> dict:
    if not MODEL_PATH.is_file():
        raise BackgroundModelError(f"Background model is unavailable: {MODEL_PATH.name}")
    try:
        with MODEL_PATH.open("rb") as stream:
            artifact = pickle.load(stream)
    except (OSError, pickle.PickleError, EOFError, AttributeError, ImportError) as error:
        raise BackgroundModelError("Background model could not be loaded safely.") from error
    if not isinstance(artifact, dict) or not artifact.get("model") or not artifact.get("features"):
        raise BackgroundModelError("Background model artifact is incomplete.")
    return artifact


def _number(value: object, name: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as error:
        raise BackgroundModelError(f"Missing numeric input: {name}") from error
    if not np.isfinite(parsed):
        raise BackgroundModelError(f"Non-finite numeric input: {name}")
    return parsed


def make_features(values: dict[str, object], location: str, *, features: list[str]) -> pd.DataFrame:
    """Build the exact feature row used by the multisite training script."""
    row = {key: _number(values.get(key), key) for key in (
        "pm2_5_ug_m3", "pm10_ug_m3", "no2_ug_m3", "so2_ug_m3", "co_ug_m3",
        "o3_ug_m3", "temperature_c", "relative_humidity_pct", "wind_speed_kmh",
        "wind_direction_deg", "hour",
    )}
    row["wind_direction_sin"] = np.sin(np.deg2rad(row.pop("wind_direction_deg")))
    row["wind_direction_cos"] = np.cos(np.deg2rad(values["wind_direction_deg"]))
    row["hour_sin"] = np.sin(2 * np.pi * row.pop("hour") / 24)
    row["hour_cos"] = np.cos(2 * np.pi * values["hour"] / 24)
    for feature in features:
        if feature.startswith("location_"):
            row[feature] = float(feature == f"location_{location}")
    missing = [feature for feature in features if feature not in row]
    if missing:
        raise BackgroundModelError(f"Model features are unsupported: {', '.join(missing)}")
    return pd.DataFrame([{feature: row[feature] for feature in features}])


def predict_next_hour(values: dict[str, object], location: str) -> float:
    """Predict one next-hour background PM2.5 value in µg/m³."""
    artifact = load_background_model()
    locations = artifact.get("locations", [])
    if location not in locations:
        raise BackgroundModelError(f"Location is not covered by the model: {location}")
    features = list(artifact["features"])
    frame = make_features(values, location, features=features)
    try:
        prediction = float(artifact["model"].predict(frame)[0])
    except (TypeError, ValueError, KeyError) as error:
        raise BackgroundModelError("Background model prediction failed.") from error
    if not np.isfinite(prediction):
        raise BackgroundModelError("Background model returned a non-finite prediction.")
    return max(0.0, prediction)
