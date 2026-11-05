"""Acquire a multi-location, multi-year atmospheric-background dataset.

The records are CAMS/Open-Meteo model output, not monitoring-station or
incident-plume ground truth. They are suitable only for a documented
background-pattern experiment.
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data" / "external" / "air_quality"
OUTPUT = OUTPUT_DIR / "open_meteo_cams_kerala_background_2024_2025_multisite.csv"
METADATA = OUTPUT_DIR / "open_meteo_cams_kerala_background_2024_2025_multisite.metadata.json"
LOCATIONS = {
    "Kochi": (9.9312, 76.2673),
    "Eloor_I": (10.079692, 76.296766),
    "Eloor_II": (10.074350, 76.303942),
}
START_DATE = "2024-01-01"
END_DATE = "2025-12-31"


def _get(url: str) -> dict:
    response = None
    for attempt in range(4):
        response = requests.get(url, timeout=180)
        if response.status_code != 429:
            break
        time.sleep(5 * (attempt + 1))
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or not isinstance(payload.get("hourly"), dict):
        raise RuntimeError("The source response did not contain an hourly object.")
    return payload


def _request(location: str, latitude: float, longitude: float) -> pd.DataFrame:
    common = f"latitude={latitude}&longitude={longitude}&start_date={START_DATE}&end_date={END_DATE}&timezone=UTC"
    weather_url = "https://archive-api.open-meteo.com/v1/archive?" + common + "&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m"
    air_url = "https://air-quality-api.open-meteo.com/v1/air-quality?" + common + "&hourly=pm2_5,pm10,nitrogen_dioxide,sulphur_dioxide,carbon_monoxide,ozone"
    weather_payload = _get(weather_url)
    air_payload = _get(air_url)
    weather = weather_payload["hourly"]
    air = air_payload["hourly"]
    weather_frame = pd.DataFrame({
        "observed_at": weather["time"], "temperature_c": weather["temperature_2m"],
        "relative_humidity_pct": weather["relative_humidity_2m"], "wind_speed_kmh": weather["wind_speed_10m"],
        "wind_direction_deg": weather["wind_direction_10m"],
    })
    air_frame = pd.DataFrame({
        "observed_at": air["time"], "pm2_5_ug_m3": air["pm2_5"], "pm10_ug_m3": air["pm10"],
        "no2_ug_m3": air["nitrogen_dioxide"], "so2_ug_m3": air["sulphur_dioxide"],
        "co_ug_m3": air["carbon_monoxide"], "o3_ug_m3": air["ozone"],
    })
    weather_frame["observed_at"] = pd.to_datetime(weather_frame["observed_at"], utc=True, errors="raise")
    air_frame["observed_at"] = pd.to_datetime(air_frame["observed_at"], utc=True, errors="raise")
    frame = weather_frame.merge(air_frame, on="observed_at", how="inner", validate="one_to_one")
    frame["location"] = location
    frame["requested_latitude"] = latitude
    frame["requested_longitude"] = longitude
    frame["returned_latitude"] = float(weather_payload.get("latitude", latitude))
    frame["returned_longitude"] = float(weather_payload.get("longitude", longitude))
    frame["source_type"] = "CAMS/Open-Meteo modelled background; not station or incident plume ground truth"
    return frame


def main() -> int:
    frames = [_request(name, *coordinates) for name, coordinates in LOCATIONS.items()]
    frame = pd.concat(frames, ignore_index=True).sort_values(["location", "observed_at"]).reset_index(drop=True)
    essential = ["observed_at", "location", "pm2_5_ug_m3", "temperature_c", "wind_speed_kmh", "wind_direction_deg"]
    if len(frame) < 50000 or frame[essential].isna().any().any():
        raise RuntimeError(f"Acquisition failed essential-field checks: rows={len(frame)}, missing={int(frame[essential].isna().sum().sum())}")
    if frame.duplicated(["location", "observed_at"]).any():
        raise RuntimeError("Duplicate location/timestamp records detected.")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    frame.to_csv(OUTPUT, index=False, date_format="%Y-%m-%dT%H:%M:%SZ")
    digest = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    metadata = {
        "dataset_id": "open_meteo_cams_kerala_background_2024_2025_multisite",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "rows": len(frame), "missing_values_by_column": frame.isna().sum().astype(int).to_dict(), "locations": LOCATIONS, "period": {"start": START_DATE, "end": END_DATE, "frequency": "hourly", "timezone": "UTC"},
        "columns": list(frame.columns), "sha256": digest,
        "sources": ["https://archive-api.open-meteo.com/v1/archive", "https://air-quality-api.open-meteo.com/v1/air-quality"],
        "use_boundary": "Modelled atmospheric background only; not measured station data, not release inventory, not incident labels, and not plume ground truth.",
        "training_status": "Eligible only for background-pattern experiments with location/time-aware validation.",
    }
    METADATA.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "metadata": str(METADATA), "rows": len(frame), "rows_per_location": frame.groupby("location").size().to_dict(), "sha256": digest}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
