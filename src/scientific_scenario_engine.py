"""Evidence-gated qualitative scenario framing; never produces probabilities or warnings."""
from __future__ import annotations
from typing import Any

HAZARDS = {
 "Flood": ["Flood"],
 "Cyclone": ["Cyclone"],
 "Earthquake": ["Earthquake"],
 "Landslide": ["Landslide"],
 "Drought": ["Drought"],
 "Heatwave": ["Heatwave"],
 "Air pollution": ["Air pollution"],
 "Industrial incident": ["Industrial incident"],
 "Compound: cyclone + flood": ["Cyclone", "Flood"],
 "Compound: heavy rainfall + drainage failure": ["Heavy rainfall", "Drainage failure"],
 "Compound: earthquake + infrastructure disruption": ["Earthquake", "Infrastructure disruption"],
}
PATHWAYS = {
 "Flood": [
  ("Hazard", "Rainfall, river overflow, coastal water, or surface-water accumulation"),
  ("Exposure", "People, buildings, roads, hospitals, utilities, and other assets in the affected footprint"),
  ("Vulnerability", "Elevation, building characteristics, drainage, access, warning time, and service dependence"),
  ("Consequence to examine", "Access disruption, inundation, service interruption, displacement, and recovery needs")],
 "Cyclone": [
  ("Hazard", "Wind, rainfall, storm surge, and coastal conditions; separate components when data permit"),
  ("Exposure", "People, buildings, lifelines, coastal areas, and essential services"),
  ("Vulnerability", "Building condition, shelter access, utility exposure, and warning lead time"),
  ("Consequence to examine", "Wind damage, flooding, access interruption, and utility outages")],
 "Earthquake": [
  ("Hazard", "Ground shaking and secondary hazards; do not infer local intensity without an appropriate model"),
  ("Exposure", "Buildings, bridges, hospitals, lifelines, and population"),
  ("Vulnerability", "Structural characteristics, construction era, code compliance, and retrofit status"),
  ("Consequence to examine", "Potential structural damage, blocked routes, and service interruption")],
 "Landslide": [
  ("Hazard", "Slope instability under relevant rainfall, geology, terrain, and land-cover conditions"),
  ("Exposure", "Settlements, roads, utilities, and facilities near susceptible slopes"),
  ("Vulnerability", "Slope modification, drainage, building condition, and evacuation access"),
  ("Consequence to examine", "Slope failure, isolation, debris blockage, and access disruption")],
 "Drought": [
  ("Hazard", "Rainfall deficit, soil moisture, streamflow, reservoir status, and duration"),
  ("Exposure", "Water supply, agriculture, ecosystems, and dependent communities"),
  ("Vulnerability", "Storage, alternative supply, demand, and distribution reliability"),
  ("Consequence to examine", "Water-supply stress, agricultural loss, and service restrictions")],
 "Heatwave": [
  ("Hazard", "Temperature and humidity over a defined period with locally appropriate thresholds"),
  ("Exposure", "Outdoor workers, sensitive groups, health facilities, and urban heat hotspots"),
  ("Vulnerability", "Cooling access, housing, health context, power reliability, and shade"),
  ("Consequence to examine", "Heat-health demand, work disruption, and cooling/water needs")],
 "Air pollution": [
  ("Hazard", "Pollutant-specific concentrations, averaging periods, monitoring quality, and meteorology"),
  ("Exposure", "People and sensitive facilities within a justified spatial/time window"),
  ("Vulnerability", "Sensitive groups, indoor protection, and access to healthcare"),
  ("Consequence to examine", "Potential exposure concerns and actions to reduce contact")],
 "Industrial incident": [
  ("Hazard", "Identified substance/process, verified incident details, weather, and authoritative guidance"),
  ("Exposure", "People and assets within a scenario-appropriate impact zone"),
  ("Vulnerability", "Shelter, evacuation routes, warning access, and response capability"),
  ("Consequence to examine", "Potential protective-action needs; AQI alone cannot identify a source")],
 "Heavy rainfall": [
  ("Hazard", "Rainfall amount, duration, spatial coverage, and antecedent wetness"),
  ("Exposure", "Low-lying locations, roads, buildings, and essential services"),
  ("Vulnerability", "Drainage capacity, blockage, tide/backwater effects, and maintenance"),
  ("Consequence to examine", "Local waterlogging and transport/service disruption")],
 "Drainage failure": [
  ("Hazard", "Documented capacity constraint, blockage, pump failure, or outfall restriction"),
  ("Exposure", "Connected drainage catchment and low-lying assets"),
  ("Vulnerability", "Redundancy, maintenance, outfall/tide conditions, and response time"),
  ("Consequence to examine", "Water accumulation and service interruption in the catchment")],
 "Infrastructure disruption": [
  ("Hazard", "Specified infrastructure failure and dependency chain"),
  ("Exposure", "Connected services, access routes, facilities, and dependent populations"),
  ("Vulnerability", "Redundancy, structural condition, backup supply, and repair access"),
  ("Consequence to examine", "Cascading service interruptions and restoration priorities")],
}
REQUIRED = {
 "Flood": ["time-stamped rainfall with units and period", "river/storm/tide reference where relevant", "documented hazard footprint or suitable hydraulic model", "validated asset locations and exposure overlay", "terrain/drainage evidence and limitations"],
 "Cyclone": ["official track/intensity source", "wind/rain/surge fields with issue time and units", "local exposure layer", "validated critical-asset locations"],
 "Earthquake": ["authoritative seismic hazard source", "site/ground conditions where relevant", "building inventory and vulnerability method", "independent impact observations for validation"],
 "Landslide": ["terrain and geology", "rainfall/antecedent wetness", "land cover and slope-change evidence", "known-event inventory for validation"],
 "Drought": ["rainfall and hydrological time series", "reservoir/supply status", "demand and catchment context", "historical drought labels for validation"],
 "Heatwave": ["time-stamped temperature and humidity", "locally justified threshold/source", "population and sensitive-facility exposure", "impact observations for evaluation"],
 "Air pollution": ["pollutant-specific monitored values and averaging period", "station metadata and QA flags", "meteorology and time alignment", "source-specific evidence before attribution"],
 "Industrial incident": ["verified incident/substance details", "authoritative safety guidance", "weather/dispersion inputs where relevant", "source records before attribution"],
 "Heavy rainfall": ["time-stamped rainfall with period", "catchment and drainage context", "validated local exposure layer", "observed waterlogging/flood records"],
 "Drainage failure": ["documented asset/failure report", "catchment connectivity", "rainfall/tide/outfall context", "maintenance and response records"],
 "Infrastructure disruption": ["verified asset/dependency inventory", "failure mode and service area", "redundancy and repair data", "observed outage/impact records"],
}

def build_scientific_scenario_frame(inputs: dict[str, Any]) -> dict[str, Any]:
    """Return qualitative pathways and evidence gates; never infer probabilities."""
    hazard = str(inputs.get("hazard", ""))
    components = list(HAZARDS.get(hazard, []))
    pathways, required = [], []
    for component in components:
        for stage, question in PATHWAYS.get(component, []):
            pathways.append({"Hazard component": component, "Reasoning stage": stage,
                "Question to investigate": question, "Status": "Not established by this form"})
        required.extend(REQUIRED.get(component, []))
    required = list(dict.fromkeys(required))
    missing = []
    if not str(inputs.get("source_and_time", "")).strip():
        missing.append("Source, timestamp, and units")
    return {
        "hazard": hazard, "components": components, "pathways": pathways,
        "required_evidence": required, "missing_provenance_fields": missing,
        "evidence_gate": "QUALITATIVE SCENARIO ONLY — insufficient evidence/method for a validated numerical prediction",
        "prediction_permitted": False, "warning_permitted": False,
        "limitations": [
            "User-entered values are not independently verified by the application.",
            "Missing data means unknown, not that hazard or exposure is absent.",
            "Scenario pathways are not calculated impacts, probabilities, or forecasts.",
            "Asset exposure requires validated locations and a suitable hazard layer.",
            "Pollution source attribution requires source-specific evidence and temporal/spatial analysis."
        ]
    }
