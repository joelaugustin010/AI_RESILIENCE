"""Evidence-aware compound cyclone/flood scenario assessment; not a forecasting model."""
from __future__ import annotations
from datetime import date
from math import isfinite
from typing import Any

from src.hazard_registry import HAZARD_REGISTRY, WORKFLOW_HAZARDS

SERVICE_PATHWAYS = {
    "Hospitals": {
        "flood": "Check ground-floor inundation, ambulance access, patient transfer routes, backup power, oxygen and medicine continuity.",
        "cyclone": "Check roof/window protection, backup power and fuel, communications, staffing access and patient shelter arrangements.",
        "compound": "A flooded access route plus cyclone-related power or communications loss can isolate patients and reduce referral capacity.",
    },
    "Roads and bridges": {
        "flood": "Check low-lying road sections, bridge approaches, underpasses, closures and alternative routes.",
        "cyclone": "Check debris, fallen trees, wind damage, coastal road exposure and travel restrictions.",
        "compound": "Flooded links and cyclone debris can remove alternate routes together, delaying evacuation and relief.",
    },
    "Electricity": {
        "flood": "Check substations, distribution equipment, repair-crew access and safe isolation procedures.",
        "cyclone": "Check overhead lines, substations, wind damage, backup generation and restoration access.",
        "compound": "Flood exposure can delay repair of cyclone-damaged equipment and extend outages.",
    },
    "Drinking water": {
        "flood": "Check source contamination, treatment plant exposure, pumping, storage and safe distribution.",
        "cyclone": "Check treatment/pumping power, source quality, supply logistics and backup arrangements.",
        "compound": "Flood contamination combined with power loss can interrupt treatment and safe water distribution.",
    },
    "Communications": {
        "flood": "Check equipment-site access, backup power and network redundancy.",
        "cyclone": "Check tower/power resilience, backup batteries, backhaul and public alert channels.",
        "compound": "Power loss and inaccessible equipment can interrupt communications during flood response.",
    },
    "Shelters": {
        "flood": "Check safe access, floor elevation, sanitation, drinking water and capacity.",
        "cyclone": "Check structural suitability, wind exposure, supplies and official shelter designation.",
        "compound": "A shelter may be reachable during one hazard but cut off when floodwater and cyclone impacts overlap.",
    },
    "Schools": {
        "flood": "Check site access, ground-floor exposure, sanitation and safe reopening criteria.",
        "cyclone": "Check building condition, roof/windows, tree hazards and any official shelter role.",
        "compound": "Damage and access disruption can extend closure and affect any shelter or relief role.",
    },
    "Drainage": {
        "flood": "Check drain capacity, blockage records, outfalls, pumping and maintenance access.",
        "cyclone": "Check debris loading, power-dependent pumps, coastal outfall conditions and maintenance access.",
        "compound": "High coastal water may restrict outfall discharge while intense rainfall increases runoff; verify local tide, outfall and pump evidence.",
    },
    "Industrial facilities": {
        "flood": "Check site elevation, hazardous-material storage, containment, drainage and safe shutdown plans.",
        "cyclone": "Check wind-rated structures, material securing, power isolation and shutdown procedures.",
        "compound": "Flooding can complicate cyclone-related shutdowns, containment and emergency access; use facility-specific plans.",
    },
}

ACTIONS = {
    "before": [
        "Verify the relevant official hazard bulletins and local-authority guidance; record issue time, valid time and source.",
        "Map exposed people and critical facilities using verified coordinates, elevation and local authority records.",
        "Review safe access routes and alternatives against the selected hazards using verified local information.",
        "Check backup power, fuel, communications, drinking water and continuity plans for critical services.",
        "Have authorized local teams verify hazard-specific conditions, critical assets and response readiness.",
    ],
    "during": [
        "Follow official warnings and evacuation orders; do not use this worksheet to decide whether to evacuate.",
        "Track only relevant observations and official bulletins with timestamps, locations, units and sources.",
        "Follow official safety instructions and avoid entering hazard-affected or restricted areas.",
        "Coordinate road closures, hospital referrals, shelter occupancy and utility status through responsible authorities.",
    ],
    "after": [
        "Use official damage and service-restoration reports to update the event record.",
        "Check drinking-water safety, electrical safety, structural safety and access before reopening facilities.",
        "Record observed impacts, timing, source and location so future evaluations use verified outcomes.",
    ],
}

def _number(value: Any, label: str) -> float | None:
    if value in (None, ""):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a number.") from exc
    if not isfinite(result):
        raise ValueError(f"{label} must be a finite number.")
    if result < 0:
        raise ValueError(f"{label} cannot be negative.")
    return result

def assess_compound_scenario(inputs: dict[str, Any]) -> dict[str, Any]:
    """Organize evidence and pathways; never invent probabilities or impacts."""
    hazards = set(inputs.get("hazards") or [])
    unknown = hazards.difference(WORKFLOW_HAZARDS)
    if unknown:
        raise ValueError(f"Unknown registered hazard selection: {sorted(unknown)}")
    custom_disaster = str(inputs.get("custom_disaster") or "").strip()
    if not hazards and not custom_disaster:
        raise ValueError("Select at least one registered hazard or describe a custom disaster.")
    area = str(inputs.get("area") or "").strip()
    if not area:
        raise ValueError("A study area is required.")

    rainfall = _number(inputs.get("rainfall_mm"), "Rainfall")
    river = _number(inputs.get("river_level_m"), "River level")
    river_ref = _number(inputs.get("river_reference_level_m"), "River reference level")
    rain_ref = _number(inputs.get("rainfall_reference_mm"), "Rainfall reference")
    cyclone_distance = _number(inputs.get("cyclone_distance_km"), "Cyclone distance")
    cyclone_wind = _number(inputs.get("cyclone_wind_knots"), "Cyclone wind")
    start, end = inputs.get("period_start"), inputs.get("period_end")
    if start is not None and not isinstance(start, date):
        raise ValueError("Scenario start date must be a date value.")
    if end is not None and not isinstance(end, date):
        raise ValueError("Scenario end date must be a date value.")
    if isinstance(start, date) and isinstance(end, date) and end < start:
        raise ValueError("Scenario end date must be on or after the start date.")

    compound = len(hazards) > 1 or any(HAZARD_REGISTRY[name].kind == "compound" for name in hazards)
    components = {component for name in hazards for component in HAZARD_REGISTRY[name].components}
    pathways = []
    for hazard in sorted(hazards):
        definition = HAZARD_REGISTRY[hazard]
        if hazard == "Flood":
            pathway = "Rainfall and river response interact with drainage, terrain, tide/backwater and land use. Verify local observations and catchment connectivity."
        elif hazard == "Cyclone":
            pathway = "Track, intensity, wind field, rainfall, coastal water and timing affect locations differently. Historical track proximity is not an impact forecast."
        else:
            pathway = definition.summary + " Required evidence: " + "; ".join(definition.evidence_factors) + "."
        pathways.append({"hazard": hazard, "pathway": pathway})
    if compound:
        pathways.append({"hazard": "Multi-hazard interaction", "pathway": "Review timing, location and shared dependencies across selected hazards. Do not assume additive risk or a causal interaction without event-aligned evidence."})
    if custom_disaster:
        pathways.append({"hazard": "Custom disaster (unregistered)", "pathway": "User-described scenario: " + custom_disaster + ". This is outside the authoritative registry and requires domain-specific evidence and expert review; no registered ML model is assigned."})

    gaps = []
    comparisons = []
    rainfall_station = str(inputs.get("rainfall_station_id") or "").strip()
    rainfall_period = str(inputs.get("rainfall_period") or "").strip()
    rainfall_reference_period = str(inputs.get("rainfall_reference_period") or "").strip()
    rainfall_reference_station = str(inputs.get("rainfall_reference_station_id") or "").strip()
    river_gauge_id = str(inputs.get("river_gauge_id") or "").strip()
    river_gauge_datum = str(inputs.get("river_gauge_datum") or "").strip()

    if rainfall is not None and rain_ref is not None:
        compatible = (
            bool(rainfall_station)
            and rainfall_station.casefold() == rainfall_reference_station.casefold()
            and bool(rainfall_period)
            and rainfall_period.casefold() == rainfall_reference_period.casefold()
        )
        if compatible:
            comparisons.append({
                "measure": "Rainfall", "observed": rainfall, "reference": rain_ref,
                "result": "At or above supplied reference" if rainfall >= rain_ref else "Below supplied reference",
                "warning": "Comparison uses the supplied station and matching accumulation period; independently verify source, units and timestamp.",
            })
        else:
            gaps.append("Rainfall reference not compared: provide matching observation/reference station IDs and accumulation periods")

    if river is not None and river_ref is not None:
        if river_gauge_id and river_gauge_datum:
            comparisons.append({
                "measure": "River level", "observed": river, "reference": river_ref,
                "result": "At or above supplied reference" if river >= river_ref else "Below supplied reference",
                "warning": "Comparison uses the supplied gauge ID and datum; independently verify the official threshold source and timestamp.",
            })
        else:
            gaps.append("River reference not compared: provide the gauge ID and documented gauge datum")

    services = [str(s) for s in (inputs.get("services") or []) if str(s) in SERVICE_PATHWAYS]
    reviews = []
    for service in services:
        info = SERVICE_PATHWAYS[service]
        points = []
        if "Flood" in components:
            points.append(info["flood"])
        if "Cyclone" in components:
            points.append(info["cyclone"])
        for selected in sorted(hazards.difference({"Flood", "Cyclone"})):
            definition = HAZARD_REGISTRY[selected]
            points.append(selected + ": " + definition.summary + " Evidence needed: " + "; ".join(definition.evidence_factors) + ".")
        if compound and {"Flood", "Cyclone"}.issubset(components):
            points.append(info["compound"])
        reviews.append({"service": service, "review_points": points})

    if "Flood" in components:
        if rainfall is None: gaps.append("Time-stamped rainfall observation and measurement interval")
        if river is None: gaps.append("Time-stamped river-level observation, gauge ID and datum")
        gaps.extend(["Verified catchment connectivity, drainage/outfall and local elevation evidence",
                     "Independent, location-specific flood outcome or inundation evidence"])
    if "Cyclone" in components:
        if cyclone_distance is None: gaps.append("Cyclone track position and time relative to the study area")
        if cyclone_wind is None: gaps.append("Source-defined cyclone intensity/wind observation and timestamp")
        gaps.append("Forecast issue time, valid time, wind/rainfall fields and coastal-water evidence")
    if compound and {"Flood", "Cyclone"}.issubset(components):
        gaps.append("Aligned cyclone, rainfall, river, tide and flood-impact timelines for the same event")
    if custom_disaster:
        gaps.append("Domain-specific authoritative definition, verified event labels, exposure data and independent validation for the custom disaster")
    if not inputs.get("evidence_source"): gaps.append("Source URL or document reference for supplied observations")
    if not inputs.get("observation_time"): gaps.append("Observation timestamp and timezone")
    if not inputs.get("evidence_type"): gaps.append("Whether this is hypothetical, historical or a current sourced observation")
    # Validate evidence metadata against expanded components, not just the
    # visible selection label. A single registered compound-hazard option must
    # receive the same component-level checks as selecting both hazards.
    if "Flood" in components:
        if rainfall is not None and not rainfall_period:
            gaps.append("Rainfall accumulation period")
        if rainfall is not None and not rainfall_station:
            gaps.append("Rainfall station ID")
        if river is not None and not river_gauge_id:
            gaps.append("River gauge ID and station location")
        if river is not None and not river_gauge_datum:
            gaps.append("River gauge datum/reference")
    if "Cyclone" in components:
        if cyclone_distance is not None and not inputs.get("cyclone_fix_time"):
            gaps.append("Cyclone track-fix timestamp")
        if "forecast" in str(inputs.get("evidence_type") or "").casefold():
            if not inputs.get("forecast_issue_time"):
                gaps.append("Forecast bulletin issue time")
            if not inputs.get("forecast_valid_time"):
                gaps.append("Forecast valid time")
        if (cyclone_distance is not None or cyclone_wind is not None) and not inputs.get("cyclone_storm_id"):
            gaps.append("Cyclone storm ID or official storm name")

    return {
        "status": "SCENARIO_REVIEW_ONLY_NOT_A_VALIDATED_FORECAST",
        "area": area, "hazards": sorted(hazards), "components": sorted(components),
        "custom_disaster": custom_disaster or None, "compound": compound,
        "period_start": str(start) if start else None, "period_end": str(end) if end else None,
        "evidence_type": str(inputs.get("evidence_type") or "Not specified"),
        "evidence_source": str(inputs.get("evidence_source") or "").strip() or None,
        "observation_time": str(inputs.get("observation_time") or "").strip() or None,
        "evidence_metadata": {
            "rainfall_period": rainfall_period or None,
            "rainfall_reference_period": rainfall_reference_period or None,
            "rainfall_station_id": rainfall_station or None,
            "rainfall_reference_station_id": rainfall_reference_station or None,
            "river_gauge_id": river_gauge_id or None,
            "river_gauge_datum": river_gauge_datum or None,
            "cyclone_storm_id": str(inputs.get("cyclone_storm_id") or "").strip() or None,
            "cyclone_fix_time": str(inputs.get("cyclone_fix_time") or "").strip() or None,
            "forecast_issue_time": str(inputs.get("forecast_issue_time") or "").strip() or None,
            "forecast_valid_time": str(inputs.get("forecast_valid_time") or "").strip() or None,
        },
        "reported_inputs": {
            "rainfall_mm": rainfall, "river_level_m": river,
            "river_reference_level_m": river_ref, "rainfall_reference_mm": rain_ref,
            "cyclone_distance_km": cyclone_distance, "cyclone_wind_knots": cyclone_wind,
            "coastal_water_or_surge_notes": str(inputs.get("coastal_water_notes") or "").strip() or None,
        },
        "reference_comparisons": comparisons, "pathways": pathways,
        "service_reviews": reviews, "actions": ACTIONS,
        "data_gaps": list(dict.fromkeys(gaps)),
        "numerical_probability_provided": False,
        "damage_or_casualty_estimate_provided": False,
        "interpretation": "Evidence-organizing scenario assessment only. It does not calculate flood/cyclone probability, inundation depth, damage, casualties or an official warning.",
    }
