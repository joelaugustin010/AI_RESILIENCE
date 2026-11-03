"""Open-Meteo/CAMS air-quality model feed for the active air-quality page.

This is intentionally separate from the historical KSPCB measurements. The
feed is a modelled estimate at Kochi coordinates, not a monitoring-station
observation and not a CPCB/KSPCB measurement.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd


OPEN_METEO_AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
KOCHI_LATITUDE = 9.9312
KOCHI_LONGITUDE = 76.2673
MODEL_SOURCE = "CAMS via Open-Meteo"
MODEL_SOURCE_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
OPEN_METEO_DOCS_URL = "https://open-meteo.com/en/docs/air-quality-api"
CAMS_ATTRIBUTION_URL = "https://atmosphere.copernicus.eu/"

POLLUTANT_VARIABLES = {
    "pm2_5": ("PM2.5", "µg/m³"),
    "pm10": ("PM10", "µg/m³"),
    "carbon_monoxide": ("CO", "µg/m³"),
    "nitrogen_dioxide": ("NO2", "µg/m³"),
    "sulphur_dioxide": ("SO2", "µg/m³"),
    "ozone": ("O3", "µg/m³"),
    "carbon_dioxide": ("CO2", "ppm"),
}
AQI_VARIABLES = {
    "european_aqi": ("European AQI", "index"),
    "us_aqi": ("US AQI", "index"),
}
REQUESTED_VARIABLES = tuple((*AQI_VARIABLES, *POLLUTANT_VARIABLES))


def aqi_category(standard: str, value: object) -> dict[str, str] | None:
    """Return the documented band for US AQI or European AQI."""
    parsed = _finite_number(value)
    if parsed is None or parsed < 0:
        return None
    key = standard.strip().upper().replace(" ", "_")
    if key in {"US_AQI", "US"}:
        bands = ((50, "Good", "#198754"), (100, "Moderate", "#d6a700"),
                 (150, "Unhealthy for sensitive groups", "#e67e22"),
                 (200, "Unhealthy", "#dc3545"), (300, "Very unhealthy", "#7b2cbf"),
                 (500, "Hazardous", "#7f1d1d"))
    elif key in {"EAQI", "EUROPEAN_AQI", "EUROPEAN"}:
        bands = ((20, "Good", "#198754"), (40, "Fair", "#d6a700"),
                 (60, "Moderate", "#d6a700"), (80, "Poor", "#e67e22"),
                 (100, "Very poor", "#7b2cbf"), (float("inf"), "Extremely poor", "#7f1d1d"))
    else:
        return None
    for upper, label, color in bands:
        if parsed <= upper:
            return {"label": label, "color": color}
    return None


class LiveAirQualityError(RuntimeError):
    """Raised when the model API response cannot be used safely."""


def _finite_number(value: object) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return parsed if math.isfinite(parsed) else None


def _get_json(url: str, *, timeout: int, opener=urlopen) -> dict[str, object]:
    request = Request(url, headers={"User-Agent": "AI_RESILIENCE air-quality dashboard"})
    if opener is urlopen:
        try:
            import requests
            response = requests.get(url, headers=dict(request.header_items()), timeout=timeout)
            response.raise_for_status()
            payload = response.json()
        except ImportError as error:
            raise LiveAirQualityError("The requests package is required for the live Open-Meteo feed.") from error
        except requests.RequestException as error:
            raise LiveAirQualityError(f"Open-Meteo connection failed: {error}") from error
        except ValueError as error:
            raise LiveAirQualityError(f"Open-Meteo returned invalid JSON: {error}") from error
    else:
        try:
            response = opener(request, timeout=timeout)
            with response:
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
            raise LiveAirQualityError(f"Open-Meteo connection failed: {error}") from error
    if not isinstance(payload, dict):
        raise LiveAirQualityError("Open-Meteo returned a non-object JSON response.")
    if payload.get("error"):
        reason = payload.get("reason") or "the API returned an error"
        raise LiveAirQualityError(f"Open-Meteo rejected the request: {reason}")
    return payload


def _validate_series(times: object, values: object, variable: str) -> list[dict[str, object]]:
    if not isinstance(times, list) or not isinstance(values, list) or len(times) != len(values):
        raise LiveAirQualityError(f"Open-Meteo returned an invalid {variable} hourly series.")
    rows = []
    label, unit = {**POLLUTANT_VARIABLES, **AQI_VARIABLES}[variable]
    for timestamp, value in zip(times, values):
        parsed_value = _finite_number(value)
        parsed_time = pd.to_datetime(timestamp, utc=True, errors="coerce")
        if parsed_value is None or pd.isna(parsed_time):
            continue
        rows.append({
            "observed_at": parsed_time,
            "pollutant": label,
            "value": parsed_value,
            "unit": unit,
            "source": MODEL_SOURCE,
        })
    return rows


def parse_open_meteo_response(payload: object) -> dict[str, object]:
    """Validate and normalize an Open-Meteo current/hourly response."""
    if not isinstance(payload, dict):
        raise LiveAirQualityError("Open-Meteo response must be a JSON object.")
    hourly = payload.get("hourly")
    if not isinstance(hourly, dict) or not isinstance(hourly.get("time"), list):
        raise LiveAirQualityError("Open-Meteo response did not contain hourly time values.")

    rows: list[dict[str, object]] = []
    for variable in REQUESTED_VARIABLES:
        if variable in hourly:
            rows.extend(_validate_series(hourly["time"], hourly[variable], variable))
    if not rows:
        raise LiveAirQualityError("Open-Meteo returned no usable air-quality values.")

    current = payload.get("current")
    current_units = payload.get("current_units")
    if not isinstance(current, dict):
        current = {}
    if not isinstance(current_units, dict):
        current_units = {}
    current_values: dict[str, dict[str, object]] = {}
    for variable in REQUESTED_VARIABLES:
        value = _finite_number(current.get(variable))
        if value is None:
            continue
        label, default_unit = {**POLLUTANT_VARIABLES, **AQI_VARIABLES}[variable]
        current_values[label] = {
            "value": value,
            "unit": str(current_units.get(variable) or default_unit),
        }
    current_time = pd.to_datetime(current.get("time"), utc=True, errors="coerce")
    return {
        "hourly": pd.DataFrame(rows),
        "current": current_values,
        "observed_at": None if pd.isna(current_time) else current_time,
        "latitude": payload.get("latitude"),
        "longitude": payload.get("longitude"),
        "timezone": payload.get("timezone", "UTC"),
    }


def fetch_open_meteo(*, latitude: float = KOCHI_LATITUDE, longitude: float = KOCHI_LONGITUDE,
                     timeout: int = 20, opener=urlopen) -> dict[str, object]:
    """Fetch the no-key Kochi CAMS/Open-Meteo model estimate."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": ",".join(REQUESTED_VARIABLES),
        "hourly": ",".join(REQUESTED_VARIABLES),
        "past_hours": 24,
        "forecast_hours": 24,
        "timezone": "UTC",
    }
    query_url = f"{OPEN_METEO_AIR_QUALITY_URL}?{urlencode(params)}"
    parsed = parse_open_meteo_response(_get_json(query_url, timeout=timeout, opener=opener))
    parsed.update({
        "status": "live",
        "source": MODEL_SOURCE,
        "source_url": MODEL_SOURCE_URL,
        "retrieved_at": datetime.now(timezone.utc),
        "request_url": query_url,
    })
    return parsed


def freshness_label(observations: pd.DataFrame, *, now: pd.Timestamp | None = None) -> str:
    """Describe age from the model timestamp, never from retrieval time."""
    if observations.empty or "observed_at" not in observations:
        return "No observation timestamp"
    latest = pd.to_datetime(observations["observed_at"], utc=True, errors="coerce").max()
    if pd.isna(latest):
        return "No observation timestamp"
    current = now or pd.Timestamp.now(tz="UTC")
    age_hours = max(0.0, (current - latest).total_seconds() / 3600)
    if age_hours <= 2:
        return f"Fresh · {age_hours:.1f} h old"
    if age_hours <= 6:
        return f"Delayed · {age_hours:.1f} h old"
    return f"Stale · {age_hours:.1f} h old"
