"""Input plausibility and hazard-specific evidence gate for scenario assessments.

This module validates user-entered observations; it is not a hazard predictor.
Completeness never substitutes for a calibrated model or verified source data.
"""
from __future__ import annotations

import math
from typing import Any

from src.hazard_registry import HAZARD_EVIDENCE_FACTORS


HAZARD_FACTORS: dict[str, tuple[str, ...]] = dict(HAZARD_EVIDENCE_FACTORS)

# Wide plausibility bounds are quality-control flags, not hazard thresholds.
NUMERIC_BOUNDS = {
    "rainfall_mm": (0.0, 1000.0, "Rainfall above 1,000 mm for the entered accumulation period is extreme; verify units, period, and source."),
    "temperature_c": (-90.0, 55.0, "Maximum air temperature is outside the broad -90°C to 55°C quality-control range; check units and whether this is air temperature rather than a surface/process temperature."),
    "normal_max_temperature_c": (-30.0, 55.0, "The station normal is outside the broad quality-control range; verify station, season, and units."),
    "wind_speed_kmh": (0.0, 400.0, "Wind speed is outside the broad 0–400 km/h quality-control range; verify units and averaging period."),
    "affected_population": (0.0, 100_000_000.0, "Population exceeds the broad 100-million context bound; verify whether the value is a count or another unit."),
}


def evaluate_scenario_readiness(hazard: str, inputs: dict[str, Any]) -> dict[str, Any]:
    """Return plausibility warnings and hazard-specific evidence gaps, never a risk score."""
    warnings: list[str] = []
    errors: list[str] = []
    checked_values: list[str] = []

    for field, (minimum, maximum, message) in NUMERIC_BOUNDS.items():
        value = inputs.get(field)
        if value is None or value == "":
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            errors.append(f"{field}: value is not numeric.")
            continue
        if not math.isfinite(numeric):
            errors.append(f"{field}: value must be finite.")
        elif numeric < minimum or numeric > maximum:
            warnings.append(f"{field}: {message}")
        else:
            checked_values.append(field)

    rainfall = inputs.get("rainfall_mm")
    if rainfall is not None and inputs.get("rainfall_period") in (None, "", "Not supplied"):
        warnings.append("Rainfall has no accumulation period; 40 mm in one hour and 40 mm over three days are not equivalent evidence.")
    if inputs.get("river_level_m") is not None:
        if not str(inputs.get("river_station") or "").strip():
            warnings.append("River level has no named station; spatial interpretation is not supported.")
        if not str(inputs.get("river_reference") or "").strip():
            warnings.append("River gauge datum/reference is missing; do not compare this level with thresholds or other stations.")
    if inputs.get("temperature_c") is not None and inputs.get("temperature_c") >= 55:
        warnings.append("Do not treat an extreme temperature entry as a valid ambient-air observation until independently checked.")

    if not str(inputs.get("source_and_time") or "").strip():
        warnings.append("Source and observation/forecast time are missing; inputs are unverified and cannot support a real-world forecast.")
    if not str(inputs.get("location") or "").strip():
        warnings.append("Location is missing; affected-area claims cannot be spatially interpreted.")

    factors = HAZARD_FACTORS.get(hazard)
    if factors is None:
        warnings.append("No hazard-specific evidence checklist is registered for this scenario.")
        factors = ()

    # Explicitly distinguish fields currently represented by the form from evidence
    # that must be documented in notes/source metadata or supplied by connected data.
    supplied = []
    missing = []
    field_map = {
        "rainfall intensity/accumulation and period": ("rainfall_mm", "rainfall_period"),
        "rainfall_mm + accumulation period": ("rainfall_mm", "rainfall_period"),
        "wind speed with averaging period": ("wind_speed_kmh", "source_and_time"),
        "maximum temperature and station normal": ("temperature_c", "normal_max_temperature_c"),
        "consecutive-day duration and qualifying station coverage": ("heatwave_consecutive_days", "heatwave_station_count"),
        "drainage condition": ("drainage_status",),
        "river level + station/datum where applicable": ("river_level_m", "river_station", "river_reference"),
    }
    for factor in factors:
        fields = field_map.get(factor)
        if fields is None:
            # Factors not directly captured as dedicated structured fields must be
            # evidenced in source metadata, notes, or authoritative connected data.
            missing.append(factor)
            continue
        present = all(
            inputs.get(field) is not None
            and inputs.get(field) != ""
            and inputs.get(field) != "Not supplied"
            for field in fields
        )
        (supplied if present else missing).append(factor)

    if inputs.get("input_classification") == "Hypothetical scenario assumption":
        warnings.append("This is a hypothetical scenario, not a report of current conditions.")
    if errors or warnings:
        input_status = "Review required"
    else:
        input_status = "Basic plausibility checks passed"

    return {
        "hazard": hazard,
        "input_status": input_status,
        "checked_fields": checked_values,
        "warnings": list(dict.fromkeys(warnings)),
        "errors": list(dict.fromkeys(errors)),
        "evidence_factors_present": supplied,
        "evidence_factors_missing_or_unverified": missing,
        "readiness": "Evidence-gated scenario review only",
        "numerical_prediction_enabled": False,
        "reason": "A complete form or plausible values do not prove a forecast. A hazard-specific model, verified source data, spatial exposure evidence, and independent validation must be available before numerical prediction is enabled.",
    }
