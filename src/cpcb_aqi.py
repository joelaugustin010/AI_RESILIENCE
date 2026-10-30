"""CPCB National AQI calculation from eligible, time-averaged pollutant inputs.

This module calculates the Indian National AQI (IND-AQI) from already
aggregated concentration records. It does not resample raw observations or
infer missing pollutants. The caller must provide the source averaging window
and the number of valid hourly observations supporting each pollutant.

Method reference:
CPCB, Report on National Air Quality Index, Tables 3.2 and 3.11 and section
3.3. The official scheme uses the maximum pollutant sub-index.
https://cpcb.nic.in/displaypdf.php?id=bmF0aW9uYWwtYWlyLXF1YWxpdHktaW5kZXgvRklOQUwtUkVQT1JUX0FRSV8ucGRm
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from typing import Any


CPCB_AQI_REPORT_URL = (
    "https://cpcb.nic.in/displaypdf.php?"
    "id=bmF0aW9uYWwtYWlyLXF1YWxpdHktaW5kZXgvRklOQUwtUkVQT1JUX0FRSV8ucGRm"
)
CPCB_MIN_VALID_HOURS = 16
CPCB_MIN_POLLUTANTS = 3
CPCB_REQUIRED_PARTICULATE = {"PM2.5", "PM10"}

# Concentration breakpoints at the upper edge of each category.
# Concentration units are part of the definition and are checked below.
# The final (Severe) category is open-ended in CPCB Table 3.11. Values above
# its lower threshold are therefore reported as a capped index of 500 rather
# than extrapolating beyond a published concentration breakpoint.
CPCB_BREAKPOINTS: dict[str, tuple[float, ...]] = {
    "PM10": (50.0, 100.0, 250.0, 350.0, 430.0),
    "PM2.5": (30.0, 60.0, 90.0, 120.0, 250.0),
    "NO2": (40.0, 80.0, 180.0, 280.0, 400.0),
    "O3": (50.0, 100.0, 168.0, 208.0, 748.0),
    "CO": (1.0, 2.0, 10.0, 17.0, 34.0),
    "SO2": (40.0, 80.0, 380.0, 800.0, 1600.0),
    "NH3": (200.0, 400.0, 800.0, 1200.0, 1800.0),
    "Pb": (0.5, 1.0, 2.0, 3.0, 3.5),
}
CPCB_UNITS = {
    "PM10": "ug/m3",
    "PM2.5": "ug/m3",
    "NO2": "ug/m3",
    "O3": "ug/m3",
    "CO": "mg/m3",
    "SO2": "ug/m3",
    "NH3": "ug/m3",
    "Pb": "ug/m3",
}
CPCB_AVERAGING_PERIODS = {
    "PM10": "24-hour",
    "PM2.5": "24-hour",
    "NO2": "24-hour",
    "O3": "8-hour",
    "CO": "8-hour",
    "SO2": "24-hour",
    "NH3": "24-hour",
    "Pb": "24-hour",
}
CPCB_AQI_CATEGORIES = (
    (0, 50, "Good", "Minimal impact"),
    (51, 100, "Satisfactory", "May cause minor breathing discomfort to sensitive people"),
    (101, 200, "Moderate", "May cause breathing discomfort to people with lung disease and discomfort to people with heart disease, children and older adults"),
    (201, 300, "Poor", "May cause breathing discomfort on prolonged exposure"),
    (301, 400, "Very Poor", "May cause respiratory illness on prolonged exposure"),
    (401, 500, "Severe", "May cause respiratory effects even on healthy people"),
)


class CPCBAQIError(ValueError):
    """Raised when an input cannot be interpreted under the CPCB AQI method."""


def cpcb_aqi_category(value: int) -> tuple[str, str]:
    """Return category and CPCB health statement for an integer AQI."""
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 500:
        raise CPCBAQIError("AQI must be an integer from 0 through 500.")
    for low, high, category, health_statement in CPCB_AQI_CATEGORIES:
        if low <= value <= high:
            return category, health_statement
    raise CPCBAQIError("AQI is outside the documented CPCB category bands.")


def calculate_pollutant_subindex(pollutant: str, concentration: float) -> dict[str, Any]:
    """Calculate a CPCB segmented-linear sub-index from Table 3.11.

    The open-ended Severe concentration band is top-coded at 500. This is an
    explicit cap, not a concentration-to-index extrapolation.
    """
    if pollutant not in CPCB_BREAKPOINTS:
        raise CPCBAQIError(f"Unsupported CPCB AQI pollutant: {pollutant!r}.")
    if isinstance(concentration, bool):
        raise CPCBAQIError("Concentration must be a finite non-negative number.")
    try:
        value = float(concentration)
    except (TypeError, ValueError, OverflowError) as error:
        raise CPCBAQIError("Concentration must be a finite non-negative number.") from error
    if not math.isfinite(value) or value < 0:
        raise CPCBAQIError("Concentration must be a finite non-negative number.")

    upper_edges = CPCB_BREAKPOINTS[pollutant]
    lower_concentration = 0.0
    lower_index = 0
    category_upper_indices = (50, 100, 200, 300, 400)

    for upper_concentration, upper_index in zip(upper_edges, category_upper_indices):
        if value <= upper_concentration:
            raw_index = lower_index + (
                (upper_index - lower_index)
                * (value - lower_concentration)
                / (upper_concentration - lower_concentration)
            )
            index = min(500, max(0, int(math.floor(raw_index + 0.5))))
            category, _ = cpcb_aqi_category(index)
            return {
                "pollutant": pollutant,
                "concentration": value,
                "unit": CPCB_UNITS[pollutant],
                "sub_index": index,
                "category": category,
                "capped_at_500": False,
                "method": "CPCB segmented-linear interpolation; Table 3.11",
            }
        lower_concentration = upper_concentration
        lower_index = upper_index

    return {
        "pollutant": pollutant,
        "concentration": value,
        "unit": CPCB_UNITS[pollutant],
        "sub_index": 500,
        "category": "Severe",
        "capped_at_500": True,
        "method": "CPCB Severe band; top-coded at 500 (no extrapolation)",
    }


def calculate_ind_aqi(
    pollutant_records: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Calculate IND-AQI from one station/location and one reporting window.

    Each record must contain pollutant, concentration, unit, averaging_period,
    and valid_hours. A record is eligible only if its averaging period matches
    CPCB's pollutant-specific period and at least 16 valid hourly observations
    support it. Overall AQI requires at least three eligible pollutants,
    including PM2.5 or PM10. Missing pollutants are never treated as zero.

    This function does not verify the source, calibration, completeness of
    source acquisition, or whether records refer to the same station/window.
    Those checks remain the caller's responsibility.
    """
    if isinstance(pollutant_records, (str, bytes, Mapping)):
        raise CPCBAQIError("Provide an iterable of pollutant record mappings.")
    try:
        records = list(pollutant_records)
    except TypeError as error:
        raise CPCBAQIError("Provide an iterable of pollutant record mappings.") from error
    if not records:
        return {
            "status": "insufficient_data",
            "aqi": None,
            "category": None,
            "dominant_pollutant": None,
            "sub_indices": [],
            "eligible_pollutant_count": 0,
            "required_pollutant_count": CPCB_MIN_POLLUTANTS,
            "missing_requirements": ["No pollutant records supplied."],
            "method": "CPCB National AQI; maximum eligible pollutant sub-index",
            "method_source": CPCB_AQI_REPORT_URL,
        }

    seen: set[str] = set()
    eligible: list[dict[str, Any]] = []
    exclusions: list[dict[str, str]] = []

    for record in records:
        if not isinstance(record, Mapping):
            raise CPCBAQIError("Every pollutant record must be a mapping.")
        pollutant = record.get("pollutant")
        if not isinstance(pollutant, str) or pollutant not in CPCB_BREAKPOINTS:
            raise CPCBAQIError(f"Unsupported or missing pollutant: {pollutant!r}.")
        if pollutant in seen:
            raise CPCBAQIError(f"Duplicate pollutant record: {pollutant}.")
        seen.add(pollutant)

        unit = record.get("unit")
        if unit != CPCB_UNITS[pollutant]:
            exclusions.append({"pollutant": pollutant, "reason": f"Expected unit {CPCB_UNITS[pollutant]}."})
            continue
        averaging_period = record.get("averaging_period")
        if averaging_period != CPCB_AVERAGING_PERIODS[pollutant]:
            exclusions.append({"pollutant": pollutant, "reason": f"Requires {CPCB_AVERAGING_PERIODS[pollutant]} averaging."})
            continue
        try:
            valid_hours = float(record.get("valid_hours"))
        except (TypeError, ValueError, OverflowError):
            valid_hours = float("nan")
        if not math.isfinite(valid_hours) or valid_hours < CPCB_MIN_VALID_HOURS:
            exclusions.append({"pollutant": pollutant, "reason": "Fewer than 16 valid hourly observations."})
            continue
        if isinstance(record.get("concentration"), bool):
            raise CPCBAQIError(f"{pollutant} concentration must be numeric.")
        try:
            concentration = float(record.get("concentration"))
        except (TypeError, ValueError, OverflowError) as error:
            raise CPCBAQIError(f"{pollutant} concentration must be numeric.") from error
        if not math.isfinite(concentration) or concentration < 0:
            raise CPCBAQIError(f"{pollutant} concentration must be finite and non-negative.")

        eligible.append(calculate_pollutant_subindex(pollutant, concentration))

    has_particulate = any(item["pollutant"] in CPCB_REQUIRED_PARTICULATE for item in eligible)
    missing: list[str] = []
    if len(eligible) < CPCB_MIN_POLLUTANTS:
        missing.append(
            f"At least {CPCB_MIN_POLLUTANTS} eligible pollutants are required; {len(eligible)} supplied."
        )
    if not has_particulate:
        missing.append("At least one eligible PM2.5 or PM10 result is required.")
    if missing:
        return {
            "status": "insufficient_data",
            "aqi": None,
            "category": None,
            "dominant_pollutant": None,
            "sub_indices": eligible,
            "eligible_pollutant_count": len(eligible),
            "required_pollutant_count": CPCB_MIN_POLLUTANTS,
            "missing_requirements": missing,
            "excluded_records": exclusions,
            "method": "CPCB National AQI; maximum eligible pollutant sub-index",
            "method_source": CPCB_AQI_REPORT_URL,
        }

    dominant = max(eligible, key=lambda item: (item["sub_index"], item["pollutant"]))
    aqi = dominant["sub_index"]
    category, health_statement = cpcb_aqi_category(aqi)
    return {
        "status": "calculated",
        "aqi": aqi,
        "category": category,
        "health_statement": health_statement,
        "dominant_pollutant": dominant["pollutant"],
        "sub_indices": sorted(eligible, key=lambda item: item["pollutant"]),
        "eligible_pollutant_count": len(eligible),
        "required_pollutant_count": CPCB_MIN_POLLUTANTS,
        "missing_requirements": [],
        "excluded_records": exclusions,
        "method": "CPCB National AQI; maximum eligible pollutant sub-index",
        "method_source": CPCB_AQI_REPORT_URL,
        "evidence_status": "CALCULATED INDICATOR",
    }
