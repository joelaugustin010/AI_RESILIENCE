"""Hazard-specific data requirements for consequence modelling in Kochi.

This is a planning and evidence-gating matrix. It does not claim the required
data are acquired, nor does it compute event probabilities, damage or warnings.
Each hazard requires a separately validated model and outcome evidence.
"""
from __future__ import annotations

from typing import Any


COMMON_REQUIREMENTS = [
    {
        "stage": "Exposure",
        "required_data": "Current official Kochi Corporation boundary; ward identifiers; geocoded population and critical assets",
        "why": "Defines who and what could be affected inside the study area.",
        "minimum_checks": "Boundary date and authority; CRS; topology; coordinate accuracy; deduplication; coverage; privacy and licence.",
        "consequence_outputs": "Population/facilities potentially intersecting a validated hazard footprint",
    },
    {
        "stage": "Vulnerability",
        "required_data": "Building/asset type, floor/elevation where relevant, construction/condition, service capacity and social vulnerability indicators",
        "why": "Exposure alone does not tell us whether an asset will be damaged or services disrupted.",
        "minimum_checks": "Representative coverage, source date, definitions, missingness, bias, and defensible spatial linkage.",
        "consequence_outputs": "Damage/service-disruption susceptibility only where supported by a calibrated vulnerability function",
    },
    {
        "stage": "Observed outcomes",
        "required_data": "Time- and location-stamped historical impacts, including affected assets/populations and event/no-event periods",
        "why": "Independent outcome labels are needed to calibrate and test consequence estimates.",
        "minimum_checks": "Event definition, completeness, reporting bias, timestamps, geolocation, independent source and holdout separation.",
        "consequence_outputs": "Validation metrics, error bounds and documented limitations",
    },
]

HAZARD_REQUIREMENTS: dict[str, dict[str, Any]] = {
    "Flood": {
        "hazard_inputs": "Rainfall time series and accumulation windows; river stage/discharge with verified gauge datum; tide/surge where relevant; observed flood extent/depth and duration.",
        "process_data": "Terrain elevation with vertical datum; land cover/imperviousness; drainage channels, culverts and capacity/condition; river/coastal boundary conditions; soil/infiltration; rainfall-runoff and hydraulic model parameters.",
        "impact_labels": "Georeferenced flood extent/depth and timing; road closures; building/facility impacts; service outages; independently documented flood/no-flood periods.",
        "model_family": "Hydrologic rainfall-runoff + hydraulic inundation model, or a carefully validated empirical baseline; not a generic classification model.",
        "current_blockers": "River gauge datum/station identity unresolved; flood raster semantics/licence unresolved; candidate ward and hospital layers not approved for exposure joins; conflicting rainfall rows must be preserved and resolved.",
        "starter_sources": "KSDMA, CWC/NWDP, IMD, NRSC/Bhuvan, INCOIS where coastal boundary conditions apply.",
    },
    "Cyclone": {
        "hazard_inputs": "Official IMD/RSMC track, intensity, wind radii/pressure where available; forecast/observed wind and rainfall; coastal surge/wave/tide observations.",
        "process_data": "Coastal elevation and bathymetry; exposure to wind/surge/rain; building fragility; shelter and evacuation access; drainage and power/water dependencies.",
        "impact_labels": "Event-linked wind/rain/surge observations, inundation, outages, damage and access disruption.",
        "model_family": "Track/intensity context plus separate wind, rainfall, surge and rainfall-flood consequence modules; best-track proximity alone is not impact prediction.",
        "current_blockers": "Best-track mirror requires comparison with official IMD workbook and reuse review; local wind/surge and impact labels not yet validated.",
        "starter_sources": "IMD/RSMC, IMD climate/data services, INCOIS, KSDMA, NRSC/Bhuvan.",
    },
    "Earthquake": {
        "hazard_inputs": "India-specific NCS and USGS event catalogues; seismic source/lineament and tectonic context; ground-motion records or defensible hazard model.",
        "process_data": "Local geology/soil amplification, site conditions, building inventory by structural type/height/age, infrastructure networks and fragility curves.",
        "impact_labels": "Observed shaking/intensity, damage grades, casualties/service interruptions with event-linked provenance.",
        "model_family": "Probabilistic seismic hazard / scenario ground motion followed by vulnerability and loss analysis; event catalogue counts are not a local damage model.",
        "current_blockers": "USGS catalogue is regional and magnitude-limited; compare with NCS/GSI evidence; no validated Kochi building inventory, ground-motion model or damage labels.",
        "starter_sources": "USGS ComCat, National Centre for Seismology, GSI, BIS seismic design references where legally available.",
    },
    "Landslide": {
        "hazard_inputs": "Rainfall intensity-duration history; slope, geology, soil, land cover and historical landslide inventory with dates.",
        "process_data": "High-resolution terrain and slope; drainage/road cuts; soil/geology; land-use change; geotechnical observations where available.",
        "impact_labels": "Validated landslide locations, event times, runout/affected area, road and building impacts, plus sampled non-event locations.",
        "model_family": "Susceptibility mapping plus event-trigger model; distinguish static susceptibility from time-specific occurrence.",
        "current_blockers": "Ernakulam GSI source archive contains three invalid source polygons; provider clarification required before spatial joins or repair.",
        "starter_sources": "GSI, KSDMA, NRSC/Bhuvan, IMD rainfall data, official district event reports.",
    },
    "Heatwave": {
        "hazard_inputs": "Daily/hourly temperature, humidity, heat index or WBGT where supported; duration and night-time minimum temperature.",
        "process_data": "Urban land-surface temperature, tree cover/shade, built density, indoor/outdoor exposure, age/health vulnerability, water and cooling access.",
        "impact_labels": "Heat-health outcomes or service strain with dates and location; baseline rates and reporting coverage.",
        "model_family": "Locally calibrated heat exposure/health model with epidemiological review; temperature alone cannot predict individual health outcomes.",
        "current_blockers": "Kochi-specific high-resolution heat exposure and health outcome labels not established; annual AQI summaries are not temperature data.",
        "starter_sources": "IMD, NRSC/Bhuvan, Kerala Health Department/official statistics, KSDMA heat-health plans.",
    },
    "Drought": {
        "hazard_inputs": "Rainfall anomalies and duration; temperature/evaporative demand; soil moisture and drought indices; reservoir/groundwater levels and flow.",
        "process_data": "Water sources, storage, demand, distribution zones, agricultural/ecological dependencies and seasonal baselines.",
        "impact_labels": "Documented water-supply restrictions, source failure, groundwater stress, crop/livelihood impacts and dates.",
        "model_family": "Multi-indicator drought monitoring plus water-supply consequence model; long-term climate normals are not current drought observations.",
        "current_blockers": "Kochi-area source/demand and impact datasets are not yet assembled at a compatible spatial and temporal scale.",
        "starter_sources": "IMD, NWDP/CWC, CGWB, Kerala Water Authority, Kerala official statistics.",
    },
    "Air pollution": {
        "hazard_inputs": "Pollutant-specific concentrations (PM2.5, PM10, NO2, SO2, O3, CO as available), timestamps, averaging periods, station coordinates and QA flags.",
        "process_data": "Meteorology and wind fields; station siting; road/traffic activity; industrial emissions/inventory and operating time; terrain/land-use context.",
        "impact_labels": "Quality-controlled observations and, only with suitable governance, health or disruption outcomes linked at appropriate scale.",
        "model_family": "Pollutant-specific temporal/spatial analysis and source-attribution methods; AQI alone cannot identify a factory.",
        "current_blockers": "Existing KSPCB annual AQI is summary data without timestamped pollutant concentrations; source-specific emissions and meteorology are needed before attribution.",
        "starter_sources": "CPCB, KSPCB, IMD, official emissions/consent records where publicly available.",
    },
    "Industrial incident": {
        "hazard_inputs": "Verified facility inventory; substance/process-specific hazard and quantity; incident history; monitoring; meteorology; official incident records.",
        "process_data": "Facility-specific safety zones and emergency plans where public; chemical/process hazard properties; wind direction/stability; drainage and transport pathways; population and critical assets.",
        "impact_labels": "Confirmed incident location/time, substance and release evidence where public, measured plume/contamination, evacuation and service impacts.",
        "model_family": "Facility- and substance-specific dispersion/impact model with expert review; generic AQI or proximity is insufficient.",
        "current_blockers": "Facility-level emissions/process data and verified incident/outcome records are incomplete; avoid unsupported attribution to named factories.",
        "starter_sources": "KSPCB, Kerala Directorate of Factories/Boilers, KSDMA, official district/industry incident reports, IMD.",
    },
    "Infrastructure failure": {
        "hazard_inputs": "Asset inventory, condition/inspection history, failure records, hazard loading and service dependencies.",
        "process_data": "Network topology for power, water, roads, drainage, telecom and hospitals; capacity, redundancy, repair time and backup duration.",
        "impact_labels": "Time-stamped failure/outage/closure and recovery records; affected service demand and restoration.",
        "model_family": "Network reliability/dependency analysis with asset-specific failure rates and validated recovery assumptions.",
        "current_blockers": "No complete, verified public network topology or consistent asset-level failure/outage history for Kochi is established.",
        "starter_sources": "Kochi Corporation, Kerala line departments, utilities, KSDMA, official transport/road datasets.",
    },
    "Compound: cyclone + flood": {
        "hazard_inputs": "Cyclone track/intensity + wind/rainfall + tide/surge + river/rainfall observations with aligned timestamps.",
        "process_data": "Coastal/river boundary conditions, terrain, drainage capacity, land cover, asset exposure and service dependencies.",
        "impact_labels": "Event-specific joint flood/surge/wind observations and impact records; separate hazard histories are not enough to prove joint probabilities.",
        "model_family": "Coupled or explicitly linked cyclone rainfall, coastal surge and inland flood modules; dependence between hazards must be modelled and validated.",
        "current_blockers": "No validated coupled Kochi flood-surge model or joint event/impact dataset; flood and cyclone evidence remains separate.",
        "starter_sources": "IMD/RSMC, INCOIS, CWC/NWDP, IMD rainfall, NRSC/Bhuvan, KSDMA.",
    },
    "Compound: heavy rainfall + drainage failure": {
        "hazard_inputs": "Time-aligned rainfall intensity/accumulation and observed drainage blockage/failure/capacity.",
        "process_data": "Drainage network, invert elevations/capacity, terrain, imperviousness, outfalls/tide levels and maintenance logs.",
        "impact_labels": "Georeferenced waterlogging depth/duration and closure/service impacts matched to rainfall and drainage status.",
        "model_family": "Urban drainage/hydraulic simulation or validated local event model; rainfall alone cannot identify drainage-caused flooding.",
        "current_blockers": "Verified drainage inventory/capacity and timestamped Kochi waterlogging outcome labels are missing.",
        "starter_sources": "Kochi Corporation, KSDMA, IMD, CWC/NWDP, NRSC/Bhuvan, INCOIS where tide-affected.",
    },
    "Compound: earthquake + infrastructure disruption": {
        "hazard_inputs": "Seismic scenario/ground motion and verified infrastructure asset locations, structural class and dependencies.",
        "process_data": "Asset fragility curves, network connectivity, redundancy, utility interdependence and repair time.",
        "impact_labels": "Observed damage/closure/outage and recovery records linked to shaking intensity.",
        "model_family": "Ground-motion scenario + fragility/loss + network dependency model with independent validation.",
        "current_blockers": "No verified Kochi network topology, building inventory or local event-linked damage labels.",
        "starter_sources": "USGS/NCS, GSI, relevant utility/line departments, KSDMA.",
    },
}


def requirements_for_hazard(hazard: str) -> dict[str, Any]:
    """Return a defensive copy of requirements for one supported hazard label."""
    record = HAZARD_REQUIREMENTS.get(hazard)
    if record is None:
        return {
            "hazard": hazard,
            "supported": False,
            "hazard_inputs": "No requirements template is registered.",
            "process_data": "Not established.",
            "impact_labels": "Not established.",
            "model_family": "No model recommendation available.",
            "current_blockers": "Do not infer a model or prediction from an unknown hazard label.",
            "starter_sources": "Not established.",
            "common_requirements": [dict(item) for item in COMMON_REQUIREMENTS],
        }
    return {
        "hazard": hazard,
        "supported": True,
        **record,
        "common_requirements": [dict(item) for item in COMMON_REQUIREMENTS],
    }


def requirements_table(hazard: str) -> list[dict[str, str]]:
    """Render hazard-specific and shared requirements as rows for the UI."""
    item = requirements_for_hazard(hazard)
    rows = [
        {"Data layer": "Hazard observations / scenarios", "Required data": item["hazard_inputs"], "Why it matters": "Defines the event's physical intensity and timing."},
        {"Data layer": "Physical process / environment", "Required data": item["process_data"], "Why it matters": "Represents the processes that transform a hazard into local effects."},
        {"Data layer": "Historical impact labels", "Required data": item["impact_labels"], "Why it matters": "Provides independent outcomes for calibration and validation."},
    ]
    for common in item["common_requirements"]:
        rows.append({
            "Data layer": common["stage"],
            "Required data": common["required_data"],
            "Why it matters": common["why"],
        })
    return rows
