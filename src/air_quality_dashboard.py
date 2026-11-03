"""Pure helpers for the compact air-quality dashboard."""

from __future__ import annotations

import math

import pandas as pd


POLLUTANT_GUIDELINES = {
    "PM2.5": {"limit": 15.0, "unit": "µg/m³", "averaging": "24-hour", "source": "WHO 2021 air-quality guideline"},
    "PM10": {"limit": 45.0, "unit": "µg/m³", "averaging": "24-hour", "source": "WHO 2021 air-quality guideline"},
    "NO2": {"limit": 25.0, "unit": "µg/m³", "averaging": "24-hour", "source": "WHO 2021 air-quality guideline"},
    "SO2": {"limit": 40.0, "unit": "µg/m³", "averaging": "24-hour", "source": "WHO 2021 air-quality guideline"},
    "O3": {"limit": 100.0, "unit": "µg/m³", "averaging": "8-hour", "source": "WHO 2021 air-quality guideline"},
    "CO": {"limit": 4000.0, "unit": "µg/m³", "averaging": "24-hour", "source": "WHO 2021 air-quality guideline (4 mg/m³)"},
}

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
