"""Evidence-aware compound cyclone/flood scenario assessment; not a forecasting model."""
from __future__ import annotations
from datetime import date
from typing import Any

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
        "Verify official IMD cyclone bulletins and KSDMA/CWC flood guidance; record issue time, valid time and source.",
        "Map exposed people and critical facilities using verified coordinates, elevation and local authority records.",
        "Confirm evacuation routes and alternatives against both flood exposure and cyclone-related access restrictions.",
        "Check backup power, fuel, communications, drinking water and continuity plans for critical services.",
        "Have authorized local teams inspect drainage, outfalls and pump status.",
    ],
    "during": [
        "Follow official warnings and evacuation orders; do not use this worksheet to decide whether to evacuate.",
        "Track rainfall, river level, tide/coastal water and cyclone bulletins with timestamps and sources.",
        "Keep people away from floodwater, damaged electrical infrastructure and exposed coastal areas.",
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
    if result < 0:
        raise ValueError(f"{label} cannot be negative.")
    return result

def assess_compound_scenario(inputs: dict[str, Any]) -> dict[str, Any]:
    """Organize evidence and pathways; never invent probabilities or impacts."""
    hazards = set(inputs.get("hazards") or [])
    if not hazards or not hazards.issubset({"Flood", "Cyclone"}):
        raise ValueError("Select Flood, Cyclone, or both.")
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
    if isinstance(start, date) and isinstance(end, date) and end < start:
        raise ValueError("Scenario end date must be on or after the start date.")

    compound = hazards == {"Flood", "Cyclone"}
    pathways = []
    if "Flood" in hazards:
        pathways.append({"hazard": "Flood", "pathway": "Rainfall and river response interact with drainage, terrain, tide/backwater and land use. Verify local observations and catchment connectivity."})
    if "Cyclone" in hazards:
        pathways.append({"hazard": "Cyclone", "pathway": "Track, intensity, wind field, rainfall, coastal water and timing affect locations differently. Historical track proximity is not an impact forecast."})
    if compound:
        pathways.append({"hazard": "Compound interaction", "pathway": "Cyclone rainfall and coastal-water conditions may coincide with river flooding or drainage limitations. Verify sequence, overlap, tide/outfall conditions and local elevations."})

    comparisons = []
    for label, observed, reference in (
        ("Rainfall", rainfall, rain_ref), ("River level", river, river_ref)
    ):
        if observed is not None and reference is not None:
            comparisons.append({
                "measure": label, "observed": observed, "reference": reference,
                "result": "At or above supplied reference" if observed >= reference else "Below supplied reference",
                "warning": "Comparison only; verify station/gauge, measurement period, units, datum, timestamp and issuing authority.",
            })

    services = [str(s) for s in (inputs.get("services") or []) if str(s) in SERVICE_PATHWAYS]
    reviews = []
    for service in services:
        info = SERVICE_PATHWAYS[service]
        points = []
        if "Flood" in hazards:
            points.append(info["flood"])
        if "Cyclone" in hazards:
            points.append(info["cyclone"])
        if compound:
            points.append(info["compound"])
        reviews.append({"service": service, "review_points": points})

    gaps = []
    if "Flood" in hazards:
        if rainfall is None: gaps.append("Time-stamped rainfall observation and measurement interval")
        if river is None: gaps.append("Time-stamped river-level observation, gauge ID and datum")
        gaps.extend(["Verified catchment connectivity, drainage/outfall and local elevation evidence",
                     "Independent, location-specific flood outcome or inundation evidence"])
    if "Cyclone" in hazards:
        if cyclone_distance is None: gaps.append("Cyclone track position and time relative to the study area")
        if cyclone_wind is None: gaps.append("Source-defined cyclone intensity/wind observation and timestamp")
        gaps.append("Official forecast issue time, valid time, wind/rainfall fields and coastal-water evidence")
    if compound:
        gaps.append("Aligned cyclone, rainfall, river, tide and flood-impact timelines for the same event")
    if not inputs.get("evidence_source"): gaps.append("Source URL or document reference for supplied observations")
    if not inputs.get("observation_time"): gaps.append("Observation timestamp and timezone")
    if not inputs.get("evidence_type"): gaps.append("Whether this is hypothetical, historical or a current sourced observation")

    return {
        "status": "SCENARIO_REVIEW_ONLY_NOT_A_VALIDATED_FORECAST",
        "area": area, "hazards": sorted(hazards), "compound": compound,
        "period_start": str(start) if start else None, "period_end": str(end) if end else None,
        "evidence_type": str(inputs.get("evidence_type") or "Not specified"),
        "evidence_source": str(inputs.get("evidence_source") or "").strip() or None,
        "observation_time": str(inputs.get("observation_time") or "").strip() or None,
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
