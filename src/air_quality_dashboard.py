"""Pure helpers for the compact air-quality dashboard."""

from __future__ import annotations

import math
import re

import pandas as pd

from src.cpcb_aqi import CPCB_AQI_CATEGORIES, calculate_pollutant_subindex


POLLUTANT_GUIDELINES = {
    "PM2.5": {"limit": 15.0, "unit": "µg/m³", "averaging": "24-hour", "source": "WHO 2021 air-quality guideline"},
    "PM10": {"limit": 45.0, "unit": "µg/m³", "averaging": "24-hour", "source": "WHO 2021 air-quality guideline"},
    "NO2": {"limit": 25.0, "unit": "µg/m³", "averaging": "24-hour", "source": "WHO 2021 air-quality guideline"},
    "SO2": {"limit": 40.0, "unit": "µg/m³", "averaging": "24-hour", "source": "WHO 2021 air-quality guideline"},
    "O3": {"limit": 100.0, "unit": "µg/m³", "averaging": "8-hour", "source": "WHO 2021 air-quality guideline"},
    "CO": {"limit": 4000.0, "unit": "µg/m³", "averaging": "24-hour", "source": "WHO 2021 air-quality guideline (4 mg/m³)"},
}

_LEGACY_REFERENCE_LIMITS = {
    "PM2.5": (60.0, "µg/m³", "24-hour"),
    "PM10": (100.0, "µg/m³", "24-hour"),
    "NO2": (80.0, "µg/m³", "24-hour"),
    "SO2": (80.0, "µg/m³", "24-hour"),
    "CO": (2.0, "mg/m³", "8-hour"),
    "O3": (100.0, "µg/m³", "8-hour"),
}


def period_matches(actual: object, expected: str) -> bool:
    """Keep explicit averaging-period validation for existing callers."""
    text = str(actual or "").casefold().replace("_", "-")
    if expected == "24-hour":
        return bool(re.search(r"(?:24\s*[- ]?hour|24\s*h(?:r|rs)?)", text))
    if expected == "8-hour":
        return bool(re.search(r"(?:8\s*[- ]?hour|8\s*h(?:r|rs)?)", text))
    return False


def classify_reference(
    value: object,
    averaging_period: object,
    quality_flag: object,
    pollutant: str,
    unit: object,
) -> tuple[str, str]:
    """Retain the validated legacy reference API alongside scenario helpers."""
    key = str(pollutant).replace("₂", "2").replace("₃", "3")
    reference = _LEGACY_REFERENCE_LIMITS.get(key)
    if reference is None:
        return "unavailable", "No reference configured"
    limit, expected_unit, expected_period = reference
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "unavailable", "No numeric observation"
    if not math.isfinite(numeric) or numeric < 0:
        return "unavailable", "No valid numeric observation"
    if str(quality_flag or "").casefold() != "valid":
        return "unavailable", "Measurement quality is not marked valid"
    normalized_unit = (
        str(unit or "").casefold().replace("μ", "u").replace("µ", "u")
        .replace("³", "3").replace(" ", "")
    )
    expected_normalized_unit = (
        expected_unit.casefold().replace("μ", "u").replace("µ", "u")
        .replace("³", "3").replace(" ", "")
    )
    if normalized_unit != expected_normalized_unit:
        return "unavailable", f"Unit must be {expected_unit}"
    if not period_matches(averaging_period, expected_period):
        return "unavailable", f"Needs a {expected_period} observation"
    if numeric <= limit:
        return "within", f"Within CPCB {expected_period} standard"
    return "above", f"Above CPCB {expected_period} standard"

SCENARIO_POLLUTANTS = {
    "PM2.5": {"unit": "µg/m³", "cpcb": "PM2.5"},
    "PM10": {"unit": "µg/m³", "cpcb": "PM10"},
    "NO2": {"unit": "µg/m³", "cpcb": "NO2"},
    "SO2": {"unit": "µg/m³", "cpcb": "SO2"},
    "CO": {"unit": "mg/m³", "cpcb": "CO"},
    "O3": {"unit": "µg/m³", "cpcb": "O3"},
    "CO2": {"unit": "ppm", "cpcb": None},
}

DISASTER_AIR_INTELLIGENCE = {
    "Flood / waterlogging": {
        "pollutants": ("PM2.5", "PM10", "CO"),
        "context": "Flooding can move dust, fuel residues, mould and combustion products; the available air feed does not measure these impacts directly.",
        "action": "Avoid flooded roads and enclosed generator/vehicle exhaust. Reassess air quality after water recedes and cleanup begins.",
    },
    "Cyclone / coastal storm": {
        "pollutants": ("PM2.5", "PM10", "NO2", "SO2", "CO"),
        "context": "Storm winds can change pollutant transport and power-generation patterns, but this page does not provide a cyclone track or dispersion model.",
        "action": "Follow IMD/KSDMA instructions first; keep combustion equipment outdoors and avoid exposure to dust or smoke during cleanup.",
    },
    "Landslide": {
        "pollutants": ("PM10", "PM2.5"),
        "context": "Slope failure and cleanup can raise dust. Air concentrations do not indicate landslide likelihood and cannot replace slope or rainfall evidence.",
        "action": "Stay clear of unstable slopes and dust-generating cleanup areas; use respiratory protection when authorities permit re-entry.",
    },
    "Drought / water scarcity": {
        "pollutants": ("PM10", "PM2.5", "O3", "NO2"),
        "context": "Dry, stagnant conditions can support dust or ozone concerns, but no drought or dispersion prediction is generated here.",
        "action": "Reduce dusty outdoor activity during elevated readings and follow verified water-supply and public-health advisories.",
    },
}


def _scenario_number(value: object) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return parsed if math.isfinite(parsed) and parsed >= 0 else None


def scenario_pollutant_values(
    current: dict[str, dict[str, object]] | None,
    hourly: pd.DataFrame | None,
    *,
    mode: str,
    overrides: dict[str, object] | None = None,
    observed_at: object = None,
) -> dict[str, dict[str, object]]:
    """Return sourced scenario values without filling missing pollutants."""
    if mode not in {"forecast", "what-if"}:
        raise ValueError("mode must be 'forecast' or 'what-if'")
    overrides = overrides or {}
    values: dict[str, dict[str, object]] = {}
    source_frame = hourly.copy() if isinstance(hourly, pd.DataFrame) else pd.DataFrame()
    if mode == "forecast" and not source_frame.empty and observed_at is not None:
        cutoff = pd.to_datetime(observed_at, utc=True, errors="coerce")
        source_frame["observed_at"] = pd.to_datetime(source_frame.get("observed_at"), utc=True, errors="coerce")
        source_frame = source_frame.loc[source_frame["observed_at"] > cutoff]
    for pollutant, specification in SCENARIO_POLLUTANTS.items():
        override = _scenario_number(overrides.get(pollutant))
        if override is not None:
            values[pollutant] = {"value": override, "unit": specification["unit"], "source": "User-entered simulated value"}
            continue
        if mode == "forecast" and not source_frame.empty:
            rows = source_frame.loc[source_frame.get("pollutant", pd.Series(dtype=str)).eq(pollutant)]
            if not rows.empty:
                row = rows.sort_values("observed_at").iloc[0]
                values[pollutant] = {"value": float(row["value"]), "unit": str(row["unit"]), "source": "External CAMS/Open-Meteo forecast"}
                continue
        item = (current or {}).get(pollutant)
        if isinstance(item, dict) and _scenario_number(item.get("value")) is not None:
            values[pollutant] = {"value": float(item["value"]), "unit": str(item.get("unit", specification["unit"])), "source": "External CAMS/Open-Meteo model estimate"}
    return values


def scenario_aqi_summary(values: dict[str, dict[str, object]]) -> dict[str, object]:
    """Calculate transparent pollutant sub-indices for a scenario, never an official AQI."""
    subindices = []
    exclusions = []
    for pollutant, item in values.items():
        cpcb_pollutant = SCENARIO_POLLUTANTS[pollutant]["cpcb"]
        if cpcb_pollutant is None:
            continue
        unit = item.get("unit")
        value = _scenario_number(item.get("value"))
        expected = SCENARIO_POLLUTANTS[pollutant]["unit"]
        if value is None or unit != expected:
            exclusions.append(f"{pollutant}: missing or incompatible unit/value")
            continue
        try:
            subindices.append(calculate_pollutant_subindex(cpcb_pollutant, value))
        except ValueError as error:
            exclusions.append(f"{pollutant}: {error}")
    eligible_names = {item["pollutant"] for item in subindices}
    can_display_index = len(subindices) >= 3 and bool(eligible_names & {"PM2.5", "PM10"})
    summary: dict[str, object] = {
        "subindices": subindices,
        "exclusions": exclusions,
        "status": "scenario_index_available" if can_display_index else "insufficient_data",
        "scenario_index": max((item["sub_index"] for item in subindices), default=None) if can_display_index else None,
        "method": "CPCB segmented-linear pollutant sub-indices applied to supplied scenario values; not an official station AQI.",
    }
    if summary["scenario_index"] is not None:
        index = int(summary["scenario_index"])
        summary["category"] = next((label for low, high, label, _ in CPCB_AQI_CATEGORIES if low <= index <= high), "Severe")
    else:
        summary["category"] = None
    return summary


def disaster_air_intelligence(values: dict[str, dict[str, object]], hazard: str) -> dict[str, object]:
    """Relate available air indicators to disaster preparedness without causal claims."""
    if hazard not in DISASTER_AIR_INTELLIGENCE:
        raise ValueError(f"Unsupported disaster context: {hazard}")
    config = DISASTER_AIR_INTELLIGENCE[hazard]
    signals = []
    for pollutant in config["pollutants"]:
        item = values.get(pollutant)
        guide = POLLUTANT_GUIDELINES.get(pollutant)
        if not item or not guide or item.get("unit") != guide["unit"]:
            continue
        value = _scenario_number(item.get("value"))
        if value is not None and value > guide["limit"]:
            signals.append({"pollutant": pollutant, "value": value, "unit": item["unit"], "source": item.get("source", "Unknown"), "reference": guide["limit"]})
    return {"hazard": hazard, "signals": signals, "context": config["context"], "action": config["action"], "status": "Air-quality precaution signal" if signals else "No compatible elevated air indicator"}

HEALTH_INFORMATION = {
    "PM2.5": {
        "summary": "Fine particles can reach deep into the lungs and may enter the bloodstream.",
        "effects": "Higher or prolonged exposure can aggravate asthma and is associated with respiratory and cardiovascular effects. Effects depend on concentration, duration and individual sensitivity.",
        "sensitive": "Children, older adults, pregnant people, and people with heart or lung disease may be more sensitive.",
        "precautions": "Reduce strenuous outdoor activity when levels are elevated, keep windows closed during peaks, and use a well-fitted respirator if exposure cannot be avoided.",
        "sources": "Traffic, combustion, industry, generators and fuel burning.",
    },
    "PM10": {
        "summary": "Coarser particles can irritate the nose, throat and airways and reduce visibility.",
        "effects": "Elevated exposure may worsen coughing, wheezing and other breathing symptoms, especially for sensitive people.",
        "sensitive": "People with asthma or other respiratory disease, children and older adults.",
        "precautions": "Limit dusty outdoor activity, avoid road/construction dust, and keep indoor spaces clean and ventilated away from peak dust.",
        "sources": "Road dust, construction, resuspended soil and industrial handling.",
    },
    "NO2": {
        "summary": "Nitrogen dioxide irritates airways and participates in the formation of secondary particles and ozone.",
        "effects": "Short-term peaks can worsen respiratory symptoms and reduce lung function in susceptible people.",
        "sensitive": "People with asthma, children and people with chronic lung disease.",
        "precautions": "Avoid heavy traffic corridors during peaks and reduce indoor combustion from unvented stoves or generators.",
        "sources": "Vehicle exhaust, generators, boilers and industrial combustion.",
    },
    "SO2": {
        "summary": "Sulphur dioxide can constrict and irritate the airways.",
        "effects": "Elevated exposure may trigger coughing, wheezing and asthma symptoms; effects vary with concentration and duration.",
        "sensitive": "People with asthma and other breathing conditions, children and older adults.",
        "precautions": "Move indoors away from the plume, avoid strenuous activity during peaks, and follow an existing asthma action plan.",
        "sources": "Sulphur-containing fuels, boilers, generators and industrial processes.",
    },
    "CO": {
        "summary": "Carbon monoxide reduces the blood's ability to carry oxygen.",
        "effects": "High exposure can cause headache, dizziness, confusion or loss of consciousness and can be life-threatening.",
        "sensitive": "Fetuses, infants, older adults, and people with heart or blood disorders.",
        "precautions": "Never use generators, charcoal appliances or vehicle engines in enclosed spaces. Leave suspected exposure immediately and contact emergency services.",
        "sources": "Incomplete combustion from engines, generators, biomass, charcoal and fuel-burning equipment.",
    },
    "O3": {
        "summary": "Ground-level ozone is a reactive pollutant formed when NOx and volatile organic compounds react in sunlight; it is different from the protective ozone layer.",
        "effects": "It can irritate the lungs and cause coughing, chest discomfort or breathing difficulty, especially during prolonged outdoor activity.",
        "sensitive": "Children, outdoor workers, people with asthma and people with chronic lung disease.",
        "precautions": "Plan strenuous outdoor activity away from afternoon peaks and reduce exposure on sunny, stagnant days.",
        "sources": "Usually a secondary pollutant formed downwind from traffic, industry and solvent emissions; a factory should not be treated as a direct ozone source without evidence.",
    },
}


def compare_pollutant(pollutant: str, value: object, unit: str, *, averaging_period: str) -> dict[str, object]:
    """Compare only like units and averaging periods; otherwise refuse assessment."""
    guideline = POLLUTANT_GUIDELINES.get(pollutant)
    if guideline is None:
        return {"status": "Cannot assess", "reason": "No selected reference limit is available."}
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = math.nan
    if not math.isfinite(parsed):
        return {"status": "Cannot assess", "reason": "The measurement is missing or invalid."}
    if unit.replace("μ", "µ") != guideline["unit"]:
        return {"status": "Cannot assess", "reason": "The measurement unit does not match the reference unit."}
    if averaging_period != guideline["averaging"]:
        return {"status": "Cannot assess", "reason": f"The reading is {averaging_period}; the reference is {guideline['averaging']}."}
    ratio = parsed / guideline["limit"]
    status = "Within reference" if ratio <= 1 else "Approaching or exceeding" if ratio <= 1.5 else "Substantially exceeds"
    return {"status": status, "difference": parsed - guideline["limit"], "ratio": ratio, "reason": guideline["source"]}


def assess_pollutant(pollutant: str, current_value: object, unit: str, hourly: pd.DataFrame) -> dict[str, object]:
    """Assess an hourly model feed using a compatible trailing mean window."""
    guideline = POLLUTANT_GUIDELINES.get(pollutant)
    if guideline is None:
        return {"status": "Reference unavailable", "color": "#64748b", "reason": "No compatible health reference is configured."}
    window_hours = 8 if guideline["averaging"] == "8-hour" else 24
    series = hourly.loc[hourly.get("pollutant", pd.Series(dtype=str)).eq(pollutant), ["observed_at", "value"]].copy()
    if series.empty:
        return {"status": "Reading available", "color": "#64748b", "reason": f"The selected reference uses a {guideline['averaging']} average; this window is unavailable."}
    series["observed_at"] = pd.to_datetime(series["observed_at"], utc=True, errors="coerce")
    series["value"] = pd.to_numeric(series["value"], errors="coerce")
    series = series.dropna().sort_values("observed_at").tail(window_hours)
    if len(series) < window_hours * 0.75:
        return {"status": "Reading available", "color": "#64748b", "reason": f"A complete {guideline['averaging']} average is not available."}
    assessed = float(series["value"].mean())
    ratio = assessed / guideline["limit"]
    if ratio <= 1:
        status, color = "Within WHO health guideline", "#198754"
    elif ratio <= 1.25:
        status, color = "Elevated", "#d6a700"
    elif ratio <= 2:
        status, color = "High — take extra care", "#e67e22"
    else:
        status, color = "Very high — reduce exposure", "#dc3545"
    return {"status": status, "color": color, "assessed_value": assessed, "ratio": ratio,
            "difference": assessed - guideline["limit"], "window": f"trailing {window_hours}-hour mean",
            "reason": guideline["source"]}


def co2_context(value: object, *, verified: bool = False) -> dict[str, str]:
    """Provide context, never an indoor safety classification, for outdoor CO2."""
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return {"status": "Unavailable", "color": "#64748b", "note": "No valid CO₂ measurement is available."}
    if not math.isfinite(parsed):
        return {"status": "Unavailable", "color": "#64748b", "note": "No valid CO₂ measurement is available."}
    return {"status": "Outdoor context only", "color": "#198754" if parsed <= 500 else "#d6a700",
            "note": "Not an indoor ventilation limit or AQI input; the value is modelled and not a verified station observation." if not verified else "Outdoor ambient context; not an indoor ventilation limit or AQI input."}


def aggregate_co2_trend(observations: pd.DataFrame, period: str) -> pd.DataFrame:
    """Aggregate only returned CO₂ observations; missing periods stay missing."""
    if period not in {"hourly", "daily", "weekly", "monthly"}:
        raise ValueError(f"Unsupported CO₂ trend period: {period}")
    if observations.empty or not {"observed_at", "value"}.issubset(observations.columns):
        return pd.DataFrame(columns=["observed_at", "value", "minimum", "maximum", "observations"])
    frame = observations.copy()
    if "pollutant" in frame.columns:
        frame = frame.loc[frame["pollutant"].eq("CO2")]
    frame["observed_at"] = pd.to_datetime(frame["observed_at"], utc=True, errors="coerce")
    frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
    frame = frame.dropna(subset=["observed_at", "value"]).sort_values("observed_at")
    if frame.empty:
        return pd.DataFrame(columns=["observed_at", "value", "minimum", "maximum", "average", "observations"])
    if period == "hourly":
        frame["period"] = frame["observed_at"].dt.floor("h")
    elif period == "daily":
        frame["period"] = frame["observed_at"].dt.floor("D")
    elif period == "weekly":
        frame["period"] = frame["observed_at"].dt.to_period("W").dt.start_time.dt.tz_localize("UTC")
    elif period == "monthly":
        frame["period"] = frame["observed_at"].dt.to_period("M").dt.start_time.dt.tz_localize("UTC")
    grouped = frame.groupby("period")["value"]
    result = grouped.agg(["mean", "min", "max", "count"]).reset_index()
    return result.rename(columns={"period": "observed_at", "mean": "value", "min": "minimum", "max": "maximum", "count": "observations"})


def evidence_category(*, measured_facility_emissions: bool = False, documented_facility_presence: bool = False) -> str:
    if measured_facility_emissions:
        return "Confirmed emissions evidence"
    if documented_facility_presence:
        return "Documented potential contributor"
    return "Insufficient evidence"
