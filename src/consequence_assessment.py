"""Evidence-gated consequence assessment contract for the core workflow.

This module defines the outputs every scenario assessment should attempt to
produce, while refusing to fabricate probabilities or affected-area claims when
validated inputs/models are absent. It is not a numerical hazard model.
"""
from __future__ import annotations

from typing import Any

from src.consequence_data_requirements import requirements_for_hazard


def assess_coastal_heatwave_screening(
    maximum_temperature_c: float | None,
    normal_maximum_temperature_c: float | None,
    consecutive_days: int | None = None,
    qualifying_stations: int | None = None,
) -> dict[str, Any]:
    """Apply an explicit station-level coastal heatwave criteria screen.

    This is not a forecast, probability model, or official warning. It screens
    supplied observations against the published IMD coastal-station criterion.
    """
    if maximum_temperature_c is None:
        station_status = "Cannot screen: maximum temperature was not supplied."
        departure = None
    elif normal_maximum_temperature_c is None:
        departure = None
        if maximum_temperature_c >= 37.0:
            station_status = (
                "Temperature is at/above the 37°C coastal threshold, but the "
                "official station-level criterion cannot be checked without the "
                "normal maximum temperature (departure must be >4.5°C)."
            )
        else:
            station_status = (
                "This supplied maximum is below the 37°C coastal threshold; this "
                "single reading does not establish or rule out a heatwave forecast."
            )
    else:
        departure = maximum_temperature_c - normal_maximum_temperature_c
        if maximum_temperature_c >= 37.0 and departure > 4.5:
            station_status = (
                "Supplied values meet the numeric IMD coastal-station screen "
                "(maximum ≥37°C and departure >4.5°C); source and observation "
                "quality still need verification."
            )
        else:
            station_status = (
                "Supplied values do not meet both numeric IMD coastal-station "
                "conditions for this reading."
            )

    declaration_conditions = (
        consecutive_days is not None
        and qualifying_stations is not None
        and consecutive_days >= 2
        and qualifying_stations >= 2
    )
    if declaration_conditions:
        declaration_status = (
            "The supplied duration/station counts meet the numeric multi-station "
            "and two-consecutive-day duration screen; this is not an official declaration."
        )
    else:
        declaration_status = (
            "Official subdivision-level declaration conditions are not established: "
            "verification is needed that criteria are met at ≥2 stations for ≥2 "
            "consecutive days. The app cannot issue official warnings."
        )
    return {
        "station_status": station_status,
        "departure_from_normal_c": departure,
        "declaration_status": declaration_status,
        "source": "IMD coastal-station criterion: maximum temperature ≥37°C and departure from normal >4.5°C; declaration duration/station rules require separate verification.",
        "is_official_warning": False,
    }


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
    heatwave_screening = None
    if hazard == "Heatwave":
        consequences.extend([
            "Heat exposure and heat-related health burden (requires local temperature/humidity, duration, population and vulnerability data)",
            "Hot-night exposure and limited overnight recovery (requires minimum-temperature observations and local normals)",
            "Outdoor-worker, older-adult, child and health-service exposure (requires validated population/asset layers and vulnerability data)",
        ])
        heatwave_screening = assess_coastal_heatwave_screening(
            data.get("temperature_c"),
            data.get("normal_max_temperature_c"),
            data.get("heatwave_consecutive_days"),
            data.get("heatwave_station_count"),
        )
    if hazard == "Drought":
        consequences.append("Water-supply stress (requires source, storage, demand and supply-disruption records)")
    if hazard == "Landslide":
        consequences.append("Slope/runout exposure (requires valid terrain, geology, event inventory and runout method)")
    if hazard == "Industrial incident":
        consequences.append("Facility-specific impact footprint (requires verified incident, substance and release conditions)")
    if hazard in {"Infrastructure failure", "Compound: heavy rainfall + drainage failure"}:
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
        "heatwave_screening": heatwave_screening,
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
