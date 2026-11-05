"""Traceable atmospheric dispersion calculations for disaster air scenarios.

This module implements a steady, continuous point-source Gaussian plume for
screening industrial/toxic releases. It is deliberately not an AI model and
does not claim validity for ash, wildfire smoke, changing cyclone fields,
complex terrain, deposition, chemistry, or exposure risk.
"""

from __future__ import annotations

import math
from typing import Any


INCIDENT_TYPES = {
    "Industrial chemical accident": "gaussian_point_source",
    "Toxic gas release": "gaussian_point_source",
    "Cyclone-related industrial accident": "gaussian_point_source_snapshot",
    "Volcanic eruption": "unavailable_specialized_model",
    "Wildfire": "unavailable_smoke_model",
}

SUPPORTED_POLLUTANTS = ("PM2.5", "PM10", "SO2", "NO2", "CO", "Other toxic gas")
STABILITY_CLASSES = ("A", "B", "C", "D", "E", "F")
LOCATION_PRESETS = {
    "Kochi model grid": (9.9312, 76.2673, "CAMS/Open-Meteo model grid"),
    "Eloor I, Methanam (KSPCB)": (10.079692, 76.296766, "KSPCB NAMP station coordinate"),
    "Eloor II, TCC (KSPCB)": (10.074350, 76.303942, "KSPCB NAMP station coordinate"),
}


class DispersionInputError(ValueError):
    """Raised for unsafe or physically invalid dispersion inputs."""


def _number(value: object, name: str, *, minimum: float | None = None) -> float:
    if isinstance(value, bool):
        raise DispersionInputError(f"{name} must be numeric.")
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise DispersionInputError(f"{name} must be numeric.") from error
    if not math.isfinite(parsed) or (minimum is not None and parsed < minimum):
        suffix = f" >= {minimum:g}" if minimum is not None else " finite"
        raise DispersionInputError(f"{name} must be{suffix}.")
    return parsed


def validate_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    """Return missing essentials without inventing defaults."""
    incident_type = str(inputs.get("incident_type", "")).strip()
    missing: list[str] = []
    if incident_type not in INCIDENT_TYPES:
        missing.append("a supported incident type")
    if incident_type in {"Volcanic eruption", "Wildfire"}:
        return {"valid": False, "missing": missing, "status": "specialized_model_unavailable", "model": INCIDENT_TYPES.get(incident_type)}
    for key, label in (("source_latitude", "incident latitude"), ("source_longitude", "incident longitude"),
                       ("release_rate_g_s", "release rate in g/s"), ("wind_speed_m_s", "wind speed in m/s"),
                       ("wind_from_deg", "wind direction from degrees"), ("release_height_m", "release height in m")):
        if inputs.get(key) in (None, ""):
            missing.append(label)
    if inputs.get("pollutant") in (None, ""):
        missing.append("released pollutant")
    if inputs.get("duration_min") in (None, ""):
        missing.append("release duration")
    try:
        if inputs.get("stability_class") not in STABILITY_CLASSES:
            missing.append("atmospheric stability class (A-F)")
    except TypeError:
        missing.append("atmospheric stability class (A-F)")
    return {"valid": not missing, "missing": missing, "status": "ready" if not missing else "missing_essentials", "model": INCIDENT_TYPES.get(incident_type)}


def _dispersion_coefficients(distance_m: float, stability: str) -> tuple[float, float]:
    """Pasquill-Gifford rural, ground-level screening coefficients."""
    x_km = distance_m / 1000.0
    # Briggs/Pasquill-Gifford rural parameterization, selected by stability.
    params = {
        "A": (0.22, 0.0001, 0.5, 0.20),
        "B": (0.16, 0.0001, 0.5, 0.12),
        "C": (0.11, 0.0001, 0.5, 0.08),
        "D": (0.08, 0.0001, 0.5, 0.06),
        "E": (0.06, 0.0001, 0.5, 0.03),
        "F": (0.04, 0.0001, 0.5, 0.016),
    }
    ay, by, az, bz = params[stability]
    sigma_y = max(1.0, ay * distance_m * (1 + by * distance_m) ** -0.5)
    sigma_z = max(1.0, az * distance_m * (1 + bz * distance_m) ** -0.5)
    return sigma_y, sigma_z


def _downwind_point(lat: float, lon: float, distance_m: float, bearing_deg: float) -> tuple[float, float]:
    radius = 6_371_000.0
    bearing = math.radians(bearing_deg)
    lat_r = math.radians(lat)
    lon_r = math.radians(lon)
    new_lat = math.asin(math.sin(lat_r) * math.cos(distance_m / radius) + math.cos(lat_r) * math.sin(distance_m / radius) * math.cos(bearing))
    new_lon = lon_r + math.atan2(math.sin(bearing) * math.sin(distance_m / radius) * math.cos(lat_r), math.cos(distance_m / radius) - math.sin(lat_r) * math.sin(new_lat))
    return math.degrees(new_lat), math.degrees(new_lon)


def gaussian_plume_concentration(*, release_rate_g_s: float, wind_speed_m_s: float, release_height_m: float,
                                 distance_m: float, stability_class: str) -> float:
    """Return centerline ground-level concentration in mg/m³."""
    q = _number(release_rate_g_s, "release rate", minimum=0.0)
    u = _number(wind_speed_m_s, "wind speed", minimum=0.01)
    h = _number(release_height_m, "release height", minimum=0.0)
    x = _number(distance_m, "distance", minimum=1.0)
    if stability_class not in STABILITY_CLASSES:
        raise DispersionInputError("stability class must be A, B, C, D, E or F.")
    sigma_y, sigma_z = _dispersion_coefficients(x, stability_class)
    concentration_g_m3 = q / (2.0 * math.pi * u * sigma_y * sigma_z) * math.exp(-0.5 * (h / sigma_z) ** 2)
    return concentration_g_m3 * 1000.0


def run_gaussian_plume(inputs: dict[str, Any], distances_m: list[float] | None = None) -> dict[str, Any]:
    """Calculate a downwind centerline screening plume and traceable map rows."""
    validation = validate_inputs(inputs)
    if not validation["valid"]:
        return {"status": validation["status"], "validation": validation, "model": validation.get("model"), "rows": []}
    distances = distances_m or [100.0, 250.0, 500.0, 1000.0, 2000.0, 5000.0]
    distances = [_number(distance, "distance", minimum=1.0) for distance in distances]
    lat = _number(inputs["source_latitude"], "incident latitude")
    lon = _number(inputs["source_longitude"], "incident longitude")
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise DispersionInputError("Incident coordinates are outside valid geographic bounds.")
    wind_from = _number(inputs["wind_from_deg"], "wind direction", minimum=0.0)
    if wind_from > 360:
        raise DispersionInputError("Wind direction must be between 0 and 360 degrees.")
    wind_speed = _number(inputs["wind_speed_m_s"], "wind speed", minimum=0.01)
    duration = _number(inputs["duration_min"], "release duration", minimum=0.01)
    bearing = (wind_from + 180.0) % 360.0
    pollutant = str(inputs["pollutant"])
    rows = []
    for distance in distances:
        concentration = gaussian_plume_concentration(
            release_rate_g_s=inputs["release_rate_g_s"], wind_speed_m_s=wind_speed,
            release_height_m=inputs["release_height_m"], distance_m=distance,
            stability_class=inputs["stability_class"],
        )
        point_lat, point_lon = _downwind_point(lat, lon, distance, bearing)
        arrival_min = distance / wind_speed / 60.0
        rows.append({"distance_m": distance, "pollutant": pollutant, "concentration_mg_m3": concentration,
                     "arrival_min": arrival_min, "latitude": point_lat, "longitude": point_lon,
                     "source": "Gaussian plume model; user-supplied source and meteorology"})
    nearest = rows[0]
    arrival = float(nearest["arrival_min"])
    timeline = []
    for time_min in (0.0, max(0.0, arrival - 1.0), arrival, arrival + duration, arrival + duration + 1.0):
        active = arrival <= time_min <= arrival + duration
        timeline.append({
            "time_min": time_min,
            "concentration_mg_m3": nearest["concentration_mg_m3"] if active else 0.0,
            "distance_m": nearest["distance_m"],
            "source": "Gaussian plume transport timing; continuous release assumption",
        })
    return {
        "status": "modelled",
        "model": "Steady continuous Gaussian point-source plume (Pasquill-Gifford rural coefficients)",
        "incident_type": inputs["incident_type"], "pollutant": pollutant, "wind_to_deg": bearing,
        "release_duration_min": duration, "rows": rows, "timeline": timeline,
        "limitations": ["centerline, steady-state screening result", "flat terrain and continuous release assumed",
                        "no deposition, chemistry, building downwash, terrain, plume rise, or exposure-dose calculation",
                        "uncertainty is material and not statistically calibrated"],
    }
