"""Kochi multi-hazard data acquisition plan and source register.

This is a discovery/provenance register, not a claim that linked datasets have
been downloaded, licensed, validated, or spatially clipped to Kochi. Source
access and terms must be checked at acquisition time. Do not infer missing
observations from absence in a portal.
"""
from __future__ import annotations

from typing import Any


DATASET_CATALOG: list[dict[str, Any]] = [
    {
        "id": "ksdma_flood_probability",
        "hazards": ["Flood", "Compound: cyclone + flood", "Compound: heavy rainfall + drainage failure"],
        "theme": "Flood hazard",
        "dataset": "Kerala flood hazard probability rasters (historic and RCP8.5 scenarios)",
        "publisher": "Kerala State Disaster Management Authority; references include UNEP/UN GRID/CIMA and RMSI/NIA",
        "url": "https://sdma.kerala.gov.in/hazard-maps/",
        "resource_urls": ["https://sdma.kerala.gov.in/wp-content/uploads/2026/06/1.-Flood-Return-Probability-Historical-10-25-50-years.zip", "https://sdma.kerala.gov.in/wp-content/uploads/2026/06/2.-Flood-Return-Probability-Historical-100-200-500-years.zip", "https://sdma.kerala.gov.in/wp-content/uploads/2026/06/3.-Flood-Return-Probability-RCP8.5-10-25-50-years.zip", "https://sdma.kerala.gov.in/wp-content/uploads/2026/06/4.-Flood-Return-Probability-RCP8.5-100-200-500-years.zip", "https://sdma.kerala.gov.in/wp-content/uploads/2022/05/Ernakulam_Hist.pdf", "https://sdma.kerala.gov.in/wp-content/uploads/2022/05/Ernakulam_RCP85.pdf"],
        "access": "Portal lists downloadable raster ZIP resources and Ernakulam PDFs; exact terms and data suitability must be checked",
        "priority": "P0",
        "status": "Discovered; not yet acquired/verified for this repository",
        "required_checks": "Inspect raster metadata, units/legend, CRS, resolution, nodata, scenario/return-period definitions, date/version, licence, and Kochi/Ernakulam overlap.",
        "limitations": "Hazard probability is not a forecast for a particular day and does not itself establish building-level exposure or damage.",
    },
    {
        "id": "ksdma_gsi_landslide",
        "hazards": ["Landslide", "Compound: heavy rainfall + drainage failure"],
        "theme": "Slope susceptibility",
        "dataset": "GSI landslide susceptibility zones for Kerala districts (2022)",
        "publisher": "Geological Survey of India, listed by KSDMA",
        "url": "https://sdma.kerala.gov.in/hazard-maps/",
        "resource_urls": ["https://sdma.kerala.gov.in/wp-content/uploads/2025/08/Ernakulam.zip"],
        "access": "District shapefile ZIP is listed by the portal; terms and layer metadata must be checked",
        "priority": "P1",
        "status": "Discovered; not yet acquired/verified for this repository",
        "required_checks": "Confirm exact Ernakulam layer availability, classification legend, scale, CRS, topology, publication version, and study-area overlap.",
        "limitations": "Susceptibility zoning is not a landslide time forecast; local slope/soil/trigger evidence remains necessary.",
    },
    {
        "id": "nwdp_cwc_rainfall",
        "hazards": ["Flood", "Cyclone", "Heatwave", "Drought", "Compound: cyclone + flood", "Compound: heavy rainfall + drainage failure"],
        "theme": "Rainfall observations",
        "dataset": "CWC telemetry rainfall, Kerala resource",
        "publisher": "Central Water Commission / National Water Data Portal",
        "url": "https://nwdp.nwic.gov.in/dataset/rainfall-cwc-telemetry-hourly",
        "access": "Portal lists state CSV resources; local file identity must be checksum-matched",
        "priority": "P0",
        "status": "Local candidate exists; portal export/checksum match and record conflicts unresolved",
        "required_checks": "Compare downloaded file hash and schema to local file; inspect station IDs, timestamps/time zone, units, duplicates/conflicts, gaps, coordinates, and coverage.",
        "limitations": "Existing local candidate has 324 conflicting station-time groups; do not silently deduplicate or convert hourly observations to rainfall accumulations.",
    },
    {
        "id": "imd_climate",
        "hazards": ["Flood", "Cyclone", "Heatwave", "Drought", "Compound: cyclone + flood"],
        "theme": "Weather and climate",
        "dataset": "IMD climate tables, historical extremes and gridded climate data",
        "publisher": "India Meteorological Department, Ministry of Earth Sciences",
        "url": "https://dsp.imdpune.gov.in/",
        "access": "Climate tables/historical extremes/gridded climate data are listed; station observations may require request/registration",
        "priority": "P0",
        "status": "Source identified; specific Kochi subset and terms not yet verified",
        "required_checks": "Choose variable and period; verify grid/station, units, timezone, temporal resolution, missingness, download terms, and spatial resolution.",
        "limitations": "Historical climate data and forecasts are different products; a climate normal cannot be used as current weather.",
    },
    {
        "id": "nrsc_bhuvan_flood",
        "hazards": ["Flood", "Cyclone", "Compound: cyclone + flood"],
        "theme": "Observed inundation and flood layers",
        "dataset": "NRSC/Bhuvan flood monitoring, historical inundation, annual layers and hazard products",
        "publisher": "National Remote Sensing Centre / ISRO",
        "url": "https://www.nrsc.gov.in/nrscnew/Apps_DMS.php?lang_code=en",
        "access": "Portal and service metadata available; each layer's download/service terms and geometry must be checked",
        "priority": "P0",
        "status": "Source identified; Kochi-compatible layer not yet acquired/verified",
        "required_checks": "Record event/date, sensor/product, CRS, pixel resolution, classification, cloud/observation limitations, licence, and overlap.",
        "limitations": "Satellite-derived inundation is an event observation/product, not a complete record of flood depth, duration, or future inundation.",
    },
    {
        "id": "bhuvan_dem_lulc",
        "hazards": ["Flood", "Landslide", "Heatwave", "Drought", "Compound: heavy rainfall + drainage failure"],
        "theme": "Terrain and land cover",
        "dataset": "NRSC/Bhuvan DEM and land-use/land-cover thematic products",
        "publisher": "National Remote Sensing Centre / ISRO",
        "url": "https://bhuvan-app1.nrsc.gov.in/2dresources/bhuvanstore.php",
        "access": "Thematic maps and WMS/WMTS are listed; use terms and data-resolution suitability must be verified",
        "priority": "P0",
        "status": "Service/catalog identified; no layer is certified for analysis yet",
        "required_checks": "Verify DEM vertical units/datum/resolution, LULC classification/year, service layer identifiers, CRS, pixel alignment, no-data, and licensed use.",
        "limitations": "Coarse DEM or dated land cover may not resolve urban drainage, underpasses, embankments, or building-scale exposure.",
    },
    {
        "id": "cpcb_realtime_aqi",
        "hazards": ["Air pollution", "Industrial incident", "Heatwave"],
        "theme": "Air quality observations",
        "dataset": "Real-time National Air Quality Index and pollutant observations",
        "publisher": "Central Pollution Control Board via Open Government Data Platform",
        "url": "https://www.data.gov.in/catalog/real-time-air-quality-index",
        "access": "Portal lists hourly data/API; API terms, keys, station coverage and field definitions must be checked",
        "priority": "P0",
        "status": "Source identified; Kochi station history not yet acquired/QA checked",
        "required_checks": "Capture station ID/coordinates, pollutant, units, averaging period, timestamps/timezone, instrument/quality flags, missingness, and API terms.",
        "limitations": "AQI alone cannot attribute pollution to a factory; source attribution needs pollutant-specific time/space evidence, meteorology and verified emissions/source data.",
    },
    {
        "id": "kerala_hazard_maps",
        "hazards": ["Flood", "Landslide", "Earthquake", "Drought", "Industrial incident", "Compound: cyclone + flood"],
        "theme": "State hazard and exposure maps",
        "dataset": "KSDMA hazard maps including earthquake incidents/lineaments, coastal susceptibility, drought, industrial accident zones and historic flood exposure",
        "publisher": "Kerala State Disaster Management Authority",
        "url": "https://sdma.kerala.gov.in/hazard-maps/",
        "resource_urls": ["https://sdma.kerala.gov.in/wp-content/uploads/2022/05/Ernakulam_Hist.pdf", "https://sdma.kerala.gov.in/wp-content/uploads/2022/05/Ernakulam_RCP85.pdf", "https://sdma.kerala.gov.in/wp-content/uploads/2025/08/Ernakulam.zip"],
        "access": "Mixed formats (maps, PDFs, raster ZIPs and shapefiles); each product requires separate metadata review",
        "priority": "P0",
        "status": "Catalogued; products not yet acquired or validated individually",
        "required_checks": "Record each product separately; inspect map scale, date, legend, coordinate reference, source agency, reuse terms and whether it covers Kochi/Ernakulam.",
        "limitations": "A map catalogue is not one harmonised dataset; layers may have different dates, scales, classifications and intended uses.",
    },
    {
        "id": "ncs_earthquake_catalog",
        "hazards": ["Earthquake", "Compound: earthquake + infrastructure disruption"],
        "theme": "Seismic events",
        "dataset": "National Center for Seismology earthquake catalogue and data-supply service",
        "publisher": "National Center for Seismology, Ministry of Earth Sciences",
        "url": "https://seismo.gov.in/datasupply",
        "access": "Catalogue and formal data-request process; waveform/strong-motion data may require a request",
        "priority": "P1",
        "status": "Source identified; historical event subset not yet acquired",
        "required_checks": "Check event completeness, magnitude type, location uncertainty, depth, time standard, station coverage and data-access terms.",
        "limitations": "An event catalogue alone cannot predict local building damage; site conditions, building inventory and engineering vulnerability are needed.",
    },
    {
        "id": "incois_coastal",
        "hazards": ["Cyclone", "Compound: cyclone + flood"],
        "theme": "Coastal sea level and storm surge",
        "dataset": "INCOIS tide-gauge, sea-level, ocean and storm-surge information",
        "publisher": "Indian National Centre for Ocean Information Services, Ministry of Earth Sciences",
        "url": "https://incois.gov.in/site/dataholdings.jsp",
        "access": "Data holdings list mixed public visualisation, registered access and no-download products",
        "priority": "P1",
        "status": "Source identified; usable Kochi tide/surge series not yet acquired",
        "required_checks": "Check station proximity, datum, units, sampling, quality control, tide/surge separation, access restrictions and temporal overlap with rainfall/river events.",
        "limitations": "Coastal conditions must not be inferred from a map screenshot; a compound model needs time-aligned and datum-compatible data.",
    },
    {
        "id": "kerala_air_quality",
        "hazards": ["Air pollution", "Industrial incident"],
        "theme": "State pollutant monitoring",
        "dataset": "Kerala State Pollution Control Board air-quality monitoring dashboard",
        "publisher": "Kerala State Pollution Control Board",
        "url": "https://www.kspcbipam.kerala.gov.in/Dashboard/airQuality",
        "access": "Dashboard displays monitoring information; downloadable historical records and stable API are not confirmed",
        "priority": "P1",
        "status": "Source identified; machine-readable historical access not confirmed",
        "required_checks": "Confirm station inventory and coordinates, pollutant data, historical export/API, QA flags, units, averaging periods and terms.",
        "limitations": "A station dashboard or annual average is insufficient for identifying a current source or causal attribution.",
    },
    {
        "id": "kerala_official_statistics",
        "hazards": ["Flood", "Cyclone", "Earthquake", "Heatwave", "Drought", "Air pollution", "Industrial incident"],
        "theme": "Population and socioeconomic exposure",
        "dataset": "Kerala Data Portal / Online Data Repository population, health, education, water, sanitation and industry statistics",
        "publisher": "Government of Kerala; Department of Economics and Statistics for ODR",
        "url": "https://datahub.kerala.gov.in/",
        "access": "Public catalogue; dataset-specific formats, granularity and terms vary",
        "priority": "P1",
        "status": "Catalogued; suitable Kochi ward-level layers not yet selected/verified",
        "required_checks": "Check reference year, geography/ward boundaries, units, denominator, suppression, aggregation level and reuse terms; do not join by ward name alone.",
        "limitations": "District-level totals cannot be assigned to individual wards or facilities without defensible spatial allocation.",
    },
    {
        "id": "ndem_multihazard",
        "hazards": ["Flood", "Cyclone", "Earthquake", "Landslide", "Drought"],
        "theme": "Multi-hazard geospatial evidence",
        "dataset": "National Database for Emergency Management / NRSC disaster-management services",
        "publisher": "National Remote Sensing Centre / ISRO and Ministry of Home Affairs",
        "url": "https://www.mha.gov.in/scheme/national-database-emergency-management-ndem-portal",
        "access": "Portal includes authorised-user functions; public pages do not guarantee unrestricted raw-data downloads",
        "priority": "P1",
        "status": "Source identified; access level and individual products must be confirmed",
        "required_checks": "Verify user eligibility, dataset-specific terms, version, metadata, coverage, and whether a public product can be reused.",
        "limitations": "Do not scrape restricted layers or assume a visible map can be redistributed as raw data.",
    },
]


def get_catalog() -> list[dict[str, Any]]:
    """Return a defensive copy of the curated discovery catalogue."""
    return [dict(item, hazards=list(item["hazards"])) for item in DATASET_CATALOG]


def validate_catalog_record(record: dict[str, Any]) -> list[str]:
    """Check catalog metadata structure, not the scientific quality of the source."""
    required = (
        "id", "hazards", "theme", "dataset", "publisher", "url", "access",
        "priority", "status", "required_checks", "limitations",
    )
    problems = [f"Missing field: {key}" for key in required if record.get(key) in (None, "", [])]
    if record.get("priority") not in {"P0", "P1", "P2"}:
        problems.append("priority must be P0, P1, or P2")
    if record.get("url") and not str(record["url"]).startswith("https://"):
        problems.append("url must use HTTPS")
    status = str(record.get("status", "")).lower()
    if "not yet" in status or "not confirmed" in status or "not acquired" in status or "not verified" in status:
        # A discovery record is explicitly not an acquisition claim.
        pass
    return problems
