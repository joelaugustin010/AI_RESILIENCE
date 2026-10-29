"""Evidence-gated consequence assessment contract for the core workflow.

This module defines the outputs every scenario assessment should attempt to
produce, while refusing to fabricate probabilities or affected-area claims when
validated inputs/models are absent. It is not a numerical hazard model.
"""
from __future__ import annotations

from typing import Any

from src.consequence_data_requirements import requirements_for_hazard


def build_consequence_assessment(
    hazard: str,
    location: str,
    input_classification: str,
    scenario_inputs: dict[str, Any] | None = None,
    *,
    validated_model_available: bool = False,
    validated_spatial_exposure_available: bool = False,
    calibrated_probability_available: bool = False,
) -> dict[str, Any]:
    """Build a complete output contract without inventing model results."""
    requirements = requirements_for_hazard(hazard)
    data = scenario_inputs or {}
    is_hypothetical = "Hypothetical" in input_classification
    known_location = bool(location and location.strip() and "not specified" not in location.lower())
    consequences = [
        "Potentially exposed population (requires validated population and hazard footprint)",
        "Critical facilities and service disruption (requires verified asset locations and vulnerability evidence)",
        "Road/bridge access and network disruption (requires validated road network and event footprint)",
        "Infrastructure/service dependencies and cascading impacts (requires network and failure evidence)",
    ]
    if hazard == "Flood" or hazard.startswith("Compound:"):
        consequences.extend([
            "Flood extent, depth and duration (requires validated hydraulic/hazard model and boundary conditions)",
            "Drainage-related waterlogging (requires drainage capacity/condition and observed waterlogging labels)",
        ])
    if hazard == "Cyclone" or hazard == "Compound: cyclone + flood":
        consequences.extend([
            "Wind exposure and coastal surge/inundation (requires official intensity, wind field and coastal boundary data)",
        ])
    if hazard == "Earthquake" or hazard == "Compound: earthquake + infrastructure disruption":
        consequences.extend([
            "Ground shaking and structural damage scenarios (requires ground-motion model, building inventory and fragility)",
        ])
    if hazard == "Air pollution":
        consequences.extend([
            "Pollutant concentration pattern (requires timestamped pollutant-specific measurements and meteorology)",
            "Potential source attribution (requires source-specific emissions and validated spatial-temporal analysis)",
        ])
    if hazard == "Heatwave":
        consequences.append("Heat exposure (requires local temperature/humidity fields and population vulnerability)")
    if hazard == "Drought":
        consequences.append("Water-supply stress (requires source, storage, demand and supply-disruption records)")
    if hazard == "Landslide":
        consequences.append("Slope/runout exposure (requires valid terrain, geology, event inventory and runout method)")
    if hazard == "Industrial incident":
        consequences.append("Facility-specific impact footprint (requires verified incident, substance and release conditions)")
    if hazard == "Infrastructure failure":
        consequences.append("Service outage and recovery (requires verified network topology, asset condition and failure data)")

    if calibrated_probability_available:
        probability_status = "A model-specific probability may be reported only with model, calibration, time horizon, spatial scale, and uncertainty."
    else:
        probability_status = "Not estimated: no validated, calibrated probability model is currently approved for this scenario."
    if validated_spatial_exposure_available and validated_model_available and known_location:
        area_status = "A model-backed affected-area estimate may be produced after the selected model runs and passes its spatial QA."
    else:
        area_status = "Not established: a validated hazard footprint/model and verified spatial exposure layer are not both available for this scenario."
    if validated_model_available:
        model_status = "A validated model is declared available for this call; its output must include version, inputs, validation metrics and uncertainty."
    else:
        model_status = "Evidence review / hypothetical scenario framing only; no validated numerical consequence model is enabled."
    missing_inputs = [
        field for field in ("source_and_time",)
        if not data.get(field)
    ]
    if hazard == "Flood":
        if data.get("river_level_m") is not None and not data.get("river_reference"):
            missing_inputs.append("river_reference")
        if data.get("rainfall_mm") is not None and not data.get("rainfall_period"):
            missing_inputs.append("rainfall_period")
    return {
        "hazard": hazard,
        "location": location,
        "scenario_type": "Hypothetical scenario" if is_hypothetical else input_classification,
        "model_status": model_status,
        "occurrence_probability": probability_status,
        "affected_area": area_status,
        "consequence_categories": list(dict.fromkeys(consequences)),
        "required_evidence": [
            requirements["hazard_inputs"],
            requirements["process_data"],
            requirements["impact_labels"],
            "Validated spatial exposure: current study boundary, population, buildings, facilities and networks",
            "Vulnerability/fragility information suitable for the selected hazard",
        ],
        "current_blockers": requirements["current_blockers"],
        "missing_context": missing_inputs,
        "probability_semantics": (
            "Occurrence probability means chance of the hazard within a defined time window. "
            "Affected-area probability means chance/intensity at a specific location. "
            "Consequence estimates describe impacts conditional on a scenario. They are not interchangeable."
        ),
        "scientific_guardrail": (
            "Do not replace unavailable probability or affected-area estimates with invented percentages, "
            "generic risk scores, or unverified ward/facility overlays."
        ),
        "prediction_permitted": bool(validated_model_available and validated_spatial_exposure_available),
        "official_warning_permitted": False,
    }
