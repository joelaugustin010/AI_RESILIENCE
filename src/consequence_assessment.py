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

    # A complete impact register makes the outputs explicit even when the
    # evidence is not yet sufficient to calculate them. Never substitute
    # population-at-risk for people actually harmed or displaced.
    impact_outputs = [
        {
            "output": "Hazard occurrence probability within a stated time horizon",
            "unit": "probability / % with horizon",
            "status": "Not estimated — calibrated, independently validated hazard model required",
            "required_evidence": "Time-stamped predictors, event labels, leakage-safe temporal validation, calibration and uncertainty intervals",
        },
        {
            "output": "Expected hazard intensity at the selected location",
            "unit": "hazard-specific physical unit",
            "status": "Not estimated — validated hazard-specific intensity model required",
            "required_evidence": "Local observations, compatible spatial inputs, verified units/datum and independent intensity validation",
        },
        {
            "output": "Forecast lead time and valid prediction window",
            "unit": "hours / days",
            "status": "Not estimated — forecast issue time, target time and demonstrated lead-time skill required",
            "required_evidence": "Timestamped forecasts, target observations and skill evaluation at each claimed lead time",
        },
        {
            "output": "Compound-hazard interaction and cascading risk",
            "unit": "joint probability / conditional impact",
            "status": "Not estimated — validated dependence and interaction model required",
            "required_evidence": "Co-occurring hazard timelines, dependence structure, component validation and compound-event impact labels",
        },
        {
            "output": "Population inside the modelled exposure footprint",
            "unit": "people",
            "status": "Not estimated — validated population grid and hazard footprint required",
            "required_evidence": "Current population grid, compatible boundary/CRS, validated event footprint and population year",
        },
        {
            "output": "People potentially needing evacuation or displacement support",
            "unit": "people",
            "status": "Not estimated — evacuation/displacement model and local vulnerability evidence required",
            "required_evidence": "Exposure, building habitability, evacuation orders, household vulnerability and shelter capacity",
        },
        {
            "output": "Injuries and fatalities",
            "unit": "people",
            "status": "Not estimated — no validated casualty model or verified outcome labels",
            "required_evidence": "Event-specific exposure, vulnerability/fragility, time-of-day, warning/response and verified outcome records",
        },
        {
            "output": "Residential and other buildings exposed or damaged",
            "unit": "buildings",
            "status": "Not estimated — validated building inventory and hazard-specific vulnerability required",
            "required_evidence": "Geocoded building inventory, occupancy/use, construction attributes and observed damage labels",
        },
        {
            "output": "Critical facilities exposed",
            "unit": "facilities",
            "status": "Not estimated — facility locations and hazard footprint require validation",
            "required_evidence": "Verified hospitals, schools, shelters, utilities and facility-level exposure overlay",
        },
        {
            "output": "Roads and essential networks affected",
            "unit": "km / network links",
            "status": "Not estimated — validated network and hazard interaction required",
            "required_evidence": "Road/bridge/utility network, closure/failure records and hazard-specific impact thresholds",
        },
        {
            "output": "Direct economic damage",
            "unit": "INR",
            "status": "Not estimated — asset values and validated damage functions required",
            "required_evidence": "Asset replacement values, event footprint, hazard intensity and locally calibrated damage functions",
        },
        {
            "output": "Essential-service outage and recovery time",
            "unit": "service-hours / days",
            "status": "Not estimated — operational failure and restoration records required",
            "required_evidence": "Service dependencies, outage start/end times, backup capacity and restoration logs",
        },
    ]
    if hazard == "Flood" or hazard.startswith("Compound:"):
        impact_outputs.append({
            "output": "Flood extent, water depth and inundation duration",
            "unit": "km² / metres / hours",
            "status": "Not estimated — validated hydraulic model and boundary conditions required",
            "required_evidence": "Terrain, drainage, river/tide boundaries, rainfall, calibrated hydraulics and observed flood marks",
        })
    if hazard in {"Cyclone", "Compound: cyclone + flood"}:
        impact_outputs.append({
            "output": "Wind and coastal-surge exposure",
            "unit": "km/h / metres",
            "status": "Not estimated — event-specific authoritative track and validated wind/surge model required",
            "required_evidence": "Official track/intensity, gust field, coastal bathymetry/topography and surge validation",
        })
    if hazard == "Heatwave":
        impact_outputs.append({
            "output": "Population heat exposure by duration and vulnerability",
            "unit": "people / person-hours",
            "status": "Not estimated — local heat field and population vulnerability data required",
            "required_evidence": "Temperature, humidity, hot-night duration, population age/occupation and health-service evidence",
        })
    if hazard == "Landslide":
        impact_outputs.append({
            "output": "Slope/runout footprint and exposed settlements",
            "unit": "km² / people",
            "status": "Not estimated — validated terrain, inventory and runout model required",
            "required_evidence": "High-resolution terrain, geology, rainfall, landslide inventory and field-validated runout",
        })
    if hazard == "Industrial incident":
        impact_outputs.append({
            "output": "Hazardous-release plume and downwind population exposure",
            "unit": "km² / people",
            "status": "Not estimated — verified release conditions and dispersion model required",
            "required_evidence": "Substance, quantity, release rate, meteorology, terrain and validated dispersion model",
        })
    if hazard == "Drought":
        impact_outputs.append({
            "output": "Population and services under water-supply stress",
            "unit": "people / service-days",
            "status": "Not estimated — supply-demand and service disruption records required",
            "required_evidence": "Reservoir/storage, source yield, demand, distribution coverage and interruption records",
        })

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
        "impact_outputs": impact_outputs,
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
