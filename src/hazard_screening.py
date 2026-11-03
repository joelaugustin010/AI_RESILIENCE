"""Transparent, input-based screening for four hazards.

This is a scenario-screening aid, not a trained model, official warning,
validated risk index, or probability calculator. It only summarizes the
condition levels explicitly supplied by the user.
"""
from __future__ import annotations

from typing import Any

HAZARD_CONFIG: dict[str, dict[str, Any]] = {
    "Flood and Urban Waterlogging": {
        "icon": "🌊",
        "description": "Heavy rainfall, river levels, drainage and local water accumulation.",
        "indicators": [
            ("rainfall", "Rainfall", "Is rainfall unusually heavy or persistent?"),
            ("river", "River or canal level", "Are nearby rivers or canals rising or already high?"),
            ("drainage", "Drainage", "Is drainage blocked, overwhelmed or causing waterlogging?"),
            ("coastal", "Tidal or backwater influence", "Is high tide or backwater influence worsening water levels?"),
        ],
        "period": "Current conditions and the next 24 hours, as described by the user",
    },
    "Cyclone and Coastal Storm Impacts": {
        "icon": "🌀",
        "description": "Official storm information, strong winds, coastal water and heavy rain.",
        "indicators": [
            ("storm", "Official storm status", "Is an official cyclone or severe-weather bulletin active for the relevant area?"),
            ("wind", "Wind conditions", "Are strong or strengthening winds being observed or forecast?"),
            ("coastal", "Coastal water conditions", "Is storm surge, coastal flooding or unusually high coastal water reported?"),
            ("rainfall", "Storm-related rainfall", "Is heavy rainfall associated with the storm reported or forecast?"),
        ],
        "period": "Use the validity period stated in the official bulletin, if available",
    },
    "Landslide": {
        "icon": "⛰️",
        "description": "Prolonged or intense rainfall, slope conditions and observed ground changes.",
        "indicators": [
            ("rainfall", "Recent rainfall", "Has there been prolonged or intense rainfall in the relevant area?"),
            ("slope", "Slope and terrain", "Is the location on or below a steep or cut slope?"),
            ("ground", "Ground or slope changes", "Have cracks, new seepage, falling material or other changes been noticed?"),
            ("history", "Local landslide history", "Are there documented past landslides close to this location?"),
        ],
        "period": "Current site conditions; no landslide forecast horizon is implied",
    },
    "Drought and Water Scarcity": {
        "icon": "☀️",
        "description": "Seasonal rainfall deficit, water sources, groundwater and supply reliability.",
        "indicators": [
            ("rainfall", "Seasonal rainfall", "Has rainfall been below the usual seasonal pattern for a sustained period?"),
            ("surface", "Surface-water availability", "Are reservoirs, ponds or local streams unusually low?"),
            ("groundwater", "Groundwater availability", "Are wells or borewells showing reduced availability?"),
            ("supply", "Water-supply reliability", "Are restrictions, shortages or supply interruptions being reported?"),
        ],
        "period": "Seasonal and multi-week conditions; not a day-to-day weather forecast",
    },
}

LEVELS = {
    "Not known / not checked": None,
    "No elevated condition reported": 0,
    "Some concern": 1,
    "Strong concern": 2,
}

def assess_hazard(values: dict[str, str]) -> dict[str, Any]:
    """Summarize user-reported levels without inventing missing observations."""
    unknown = [key for key, value in values.items() if value not in LEVELS]
    if unknown:
        raise ValueError("Unknown condition level supplied.")
    known = [LEVELS[value] for value in values.values() if LEVELS[value] is not None]
    if not known:
        category = "Insufficient information"
        explanation = "No condition indicators were assessed. Add verified observations before drawing conclusions."
    elif max(known) == 2:
        category = "Elevated concern reported"
        explanation = "At least one selected condition was marked as strong concern. This is a screening flag, not a measured hazard probability."
    elif max(known) == 1:
        category = "Some concern reported"
        explanation = "At least one selected condition was marked as some concern. Check the source, location and time of each observation."
    else:
        category = "No elevated indicators reported"
        explanation = "All assessed indicators were marked as having no elevated condition. This does not establish that the area is safe or hazard-free."
    return {
        "category": category,
        "explanation": explanation,
        "assessed_count": len(known),
        "unknown_count": len(values) - len(known),
        "indicator_count": len(values),
        "method": "User-input condition screening (not a trained or validated predictive model)",
        "probability": None,
        "risk_score": None,
    }

def assess_all_hazards(inputs: dict[str, dict[str, str]]) -> dict[str, dict[str, Any]]:
    """Return an assessment card for each configured hazard."""
    missing = [name for name in HAZARD_CONFIG if name not in inputs]
    if missing:
        raise ValueError("Missing hazard inputs: " + ", ".join(missing))
    return {name: assess_hazard(inputs[name]) for name in HAZARD_CONFIG}
