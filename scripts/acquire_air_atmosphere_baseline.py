"""Acquire a provenance-labelled atmospheric background dataset for Kochi.

This does not create disaster-incident labels. Open-Meteo/CAMS values are
modelled atmospheric background data and must not be used as station or plume
ground truth without independent validation.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data" / "external" / "air_quality"
OUTPUT = OUTPUT_DIR / "open_meteo_cams_kochi_background_2024_2025.csv"
METADATA = OUTPUT_DIR / "open_meteo_cams_kochi_background_2024_2025.metadata.json"
LATITUDE = 9.9312
LONGITUDE = 76.2673
START_DATE = "2024-01-01"
END_DATE = "2025-12-31"


def _get(url: str) -> dict:
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or not isinstance(payload.get("hourly"), dict):
        raise RuntimeError("The source response did not contain an hourly object.")
    return payload


def _tidy(payload: dict, required: list[str]) -> pd.DataFrame:
    hourly = payload["hourly"]
    missing = [key for key in required if key not in hourly]
    if missing:
        raise RuntimeError("Missing source fields: " + ", ".join(missing))
    frame = pd.DataFrame({key: hourly[key] for key in required})
    if frame.empty or frame["time"].duplicated().any():
        raise RuntimeError("The source returned an empty or duplicated hourly series.")
    frame["observed_at"] = pd.to_datetime(frame.pop("time"), utc=True, errors="coerce")
    if frame["observed_at"].isna().any():
        raise RuntimeError("The source returned invalid timestamps.")
    rename = {
        "temperature_2m": "temperature_c", "relative_humidity_2m": "relative_humidity_pct",
        "wind_speed_10m": "wind_speed_kmh", "wind_direction_10m": "wind_direction_deg",
        "pm2_5": "pm2_5_ug_m3", "pm10": "pm10_ug_m3", "nitrogen_dioxide": "no2_ug_m3",
        "sulphur_dioxide": "so2_ug_m3", "carbon_monoxide": "co_ug_m3", "ozone": "o3_ug_m3",
    }
    frame = frame.rename(columns=rename)
    frame["latitude"] = float(payload.get("latitude", LATITUDE))
    frame["longitude"] = float(payload.get("longitude", LONGITUDE))
    frame["source_type"] = "CAMS/Open-Meteo modelled background; not station or incident plume ground truth"
    frame = frame.sort_values("observed_at").reset_index(drop=True)
    if frame.isna().all(axis=0).any():
        raise RuntimeError("At least one requested source field is entirely missing.")
    return frame


def main() -> int:
    weather_url = (
        "https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}"
        "&start_date={start}&end_date={end}&hourly=temperature_2m,relative_humidity_2m,"
        "wind_speed_10m,wind_direction_10m&timezone=UTC"
    ).format(lat=LATITUDE, lon=LONGITUDE, start=START_DATE, end=END_DATE)
    air_url = (
        "https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lon}"
        "&start_date={start}&end_date={end}&hourly=pm2_5,pm10,nitrogen_dioxide,"
        "sulphur_dioxide,carbon_monoxide,ozone&timezone=UTC"
    ).format(lat=LATITUDE, lon=LONGITUDE, start=START_DATE, end=END_DATE)
    weather = _get(weather_url)
    air = _get(air_url)
    weather_hourly = {key: weather["hourly"][key] for key in ("time", "temperature_2m", "relative_humidity_2m", "wind_speed_10m", "wind_direction_10m")}
    air_hourly = {key: air["hourly"][key] for key in ("time", "pm2_5", "pm10", "nitrogen_dioxide", "sulphur_dioxide", "carbon_monoxide", "ozone")}
    weather_frame = _tidy({"hourly": weather_hourly, "latitude": weather.get("latitude"), "longitude": weather.get("longitude")}, list(weather_hourly))
    air_frame = _tidy({"hourly": air_hourly, "latitude": air.get("latitude"), "longitude": air.get("longitude")}, list(air_hourly))
    weather_frame = weather_frame.drop(columns=["latitude", "longitude", "source_type"], errors="ignore")
    air_frame = air_frame.drop(columns=["temperature_c", "relative_humidity_pct", "wind_speed_kmh", "wind_direction_deg", "latitude", "longitude", "source_type"], errors="ignore")
    frame = weather_frame.merge(air_frame, on="observed_at", how="inner", validate="one_to_one")
    if len(frame) < 10000:
        raise RuntimeError(f"Only {len(frame)} aligned hourly records were returned; refusing incomplete acquisition.")
    frame["latitude"] = float(air.get("latitude", LATITUDE))
    frame["longitude"] = float(air.get("longitude", LONGITUDE))
    frame["source_type"] = "CAMS/Open-Meteo modelled background; not station or incident plume ground truth"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    frame.to_csv(OUTPUT, index=False, date_format="%Y-%m-%dT%H:%M:%SZ")
    digest = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    metadata = {
        "dataset_id": "open_meteo_cams_kochi_background_2024_2025",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "rows": len(frame), "columns": list(frame.columns), "sha256": digest,
        "location": {"requested_latitude": LATITUDE, "requested_longitude": LONGITUDE, "returned_latitude": frame["latitude"].iloc[0], "returned_longitude": frame["longitude"].iloc[0]},
        "period": {"start": START_DATE, "end": END_DATE, "timestamp_timezone": "UTC", "frequency": "hourly"},
        "sources": [{"name": "Open-Meteo Historical Weather API", "url": weather_url}, {"name": "Open-Meteo Air Quality API / CAMS", "url": air_url}],
        "use_boundary": "Atmospheric background/context only. Not measured station data, not a release inventory, not incident labels, and not ground truth for plume concentrations.",
        "training_status": "Not a supervised disaster-plume training table; no incident target is present.",
    }
    METADATA.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "metadata": str(METADATA), "rows": len(frame), "sha256": digest}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
