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
        "resource_urls": ["https://sdma.kerala.gov.in/wp-content/uploads/2026/06/1.-Flood-Return-Probability-Historical-10-25-50-years.zip", "https://sdma.kerala.gov.in/wp-content/uploads/2026/06/2.Flood-Return-Probability-Historical-100-200-500-years.zip", "https://sdma.kerala.gov.in/wp-content/uploads/2026/06/3.-Flood-Return-Probability-RCP8.5-10-25-50-years.zip", "https://sdma.kerala.gov.in/wp-content/uploads/2026/06/4.Flood-Return-Probability-RCP8.5-100-200-500-years.zip", "https://sdma.kerala.gov.in/wp-content/uploads/2022/05/Ernakulam_Hist.pdf", "https://sdma.kerala.gov.in/wp-content/uploads/2022/05/Ernakulam_RCP85.pdf"],
        "access": "Portal lists downloadable raster ZIP resources and Ernakulam PDFs; exact terms and data suitability must be checked",
        "priority": "P0",
        "status": "Local raw archive exists and ZIP CRC was checked; valid pixel meaning and reuse terms remain unresolved, so it is excluded from model sampling.",
        "required_checks": "Existing metadata reports EPSG:4326, 3004x5371 float32 rasters and CRC success, but no documented valid-pixel units/semantics. Confirm licence, inspect each raster, and establish Kochi/Ernakulam overlap before any use.",
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
        "id": "kerala_sw_rainfall_telemetry_2021_2025",
        "hazards": ["Flood", "Cyclone", "Compound: cyclone + flood", "Compound: heavy rainfall + drainage failure"],
        "theme": "Rainfall observations",
        "dataset": "Kerala Surface Water Department telemetry rainfall (hourly), 2021-2025",
        "publisher": "Kerala Surface Water Department via National Water Data Portal / National Water Informatics Centre",
        "url": "https://nwdp.nwic.gov.in/dataset/09518a17-a04b-43e3-a4e0-3d0fe81dbf68/resource/0410ec7a-b253-4d85-8f0f-e6b69c44e40c/download/rainfall_tel_hr_kerala_sw_kl_2021_2025.csv",
        "resource_urls": ["https://nwdp.nwic.gov.in/dataset/09518a17-a04b-43e3-a4e0-3d0fe81dbf68/resource/0410ec7a-b253-4d85-8f0f-e6b69c44e40c/download/rainfall_tel_hr_kerala_sw_kl_2021_2025.csv"],
        "access": "Acquired in workflow run 40928550082; raw CSV and SHA-256 manifest are in the private short-lived artifact, not committed to Git.",
        "priority": "P0",
        "status": "Downloaded and descriptively audited: 188,045 rows, 108 stations, 14,347 Ernakulam rows across 9 named stations; zero invalid timestamps/numeric values and zero duplicate station-time groups in this file.",
        "required_checks": "Confirm station coordinates/CRS and accuracy, source timezone, irregular observation gaps, instrument/quality flags, temporal sampling, current licence terms and alignment to verified flood-event periods.",
        "limitations": "Rows span 2021-04-07 to 2025-03-09; some stations have very long gaps. Ernakulam district coverage is not equivalent to Kochi Corporation coverage. This is rainfall input, not a flood/no-flood label or current forecast."
    },
    {
        "id": "kerala_sw_river_level_telemetry_2021_2025",
        "hazards": ["Flood", "Compound: cyclone + flood"],
        "theme": "River-level observations",
        "dataset": "Kerala Surface Water Department telemetry river level, 2021-2025",
        "publisher": "Kerala Surface Water Department via National Water Data Portal / National Water Informatics Centre",
        "url": "https://nwdp.nwic.gov.in/dataset/1a00209e-c864-4c1c-bc82-b5e2d8ecb66e/resource/0af0acba-517c-4278-bf77-ff137eb3c2cf/download/rwl_tel_hr_kerala_sw_999_2021_2025.csv",
        "resource_urls": ["https://nwdp.nwic.gov.in/dataset/1a00209e-c864-4c1c-bc82-b5e2d8ecb66e/resource/0af0acba-517c-4278-bf77-ff137eb3c2cf/download/rwl_tel_hr_kerala_sw_999_2021_2025.csv"],
        "access": "Acquired and structurally audited in workflow run 40928550082; raw CSV and SHA-256 manifest are in the private short-lived artifact.",
        "priority": "P0",
        "status": "Downloaded and descriptively audited: 465,076 rows, 26 stations, 35,337 Ernakulam rows at two source-reported stations; no duplicate station-time groups in this download.",
        "required_checks": "Resolve vertical gauge datum/reference and timezone, validate station identity and river/basin metadata with provider, inspect gaps and official station-specific warning thresholds, then align with independent event evidence.",
        "limitations": "River stage is not flood depth. No threshold comparison or spatial exposure claim is permitted until datum, station identity and local warning threshold are verified."
    },
    {
        "id": "kerala_sw_river_level_manual_2021_2025",
        "hazards": ["Flood", "Compound: cyclone + flood"],
        "theme": "River-level observations",
        "dataset": "Kerala Surface Water Department manual river level, 2021-2025",
        "publisher": "Kerala Surface Water Department via National Water Data Portal / National Water Informatics Centre",
        "url": "https://nwdp.nwic.gov.in/dataset/b7ed6f63-d702-429b-a342-c3e2acd31ad6/resource/fe95a85e-142d-4acf-83fc-24499afc546b/download/rwl_manual_hr_kerala_sw_031_2021_2025.csv",
        "resource_urls": ["https://nwdp.nwic.gov.in/dataset/b7ed6f63-d702-429b-a342-c3e2acd31ad6/resource/fe95a85e-142d-4acf-83fc-24499afc546b/download/rwl_manual_hr_kerala_sw_031_2021_2025.csv"],
        "access": "Acquired and audited in workflow run 40928550082; raw CSV and SHA-256 manifest are in the private short-lived artifact.",
        "priority": "P1",
        "status": "Downloaded and descriptively audited: 16,005 rows from 6 stations; zero source rows were labelled Ernakulam in this download.",
        "required_checks": "Confirm geographic coverage, gauge reference, source timezone, irregular sampling and inconsistent river/basin labels with provider before use.",
        "limitations": "This manual dataset is not Kochi-specific in the audited records and cannot supply Kochi labels without verified spatial and station identity evidence."
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
        "status": "Mixed status: historical flood raster archive acquired and integrity-checked but excluded from modeling; Ernakulam PDFs and GSI ZIP are source-linked; each product still needs separate review.",
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
        "status": "Dated KSPCB daily/monthly reports and annual AQI summaries already acquired into project records; live feed remains blocked and source attribution is not established.",
        "required_checks": "Audit the existing dated reports and processed CSVs; confirm station inventory/coordinates, pollutant units, averaging periods, completeness, current consent/emissions evidence and terms.",
        "limitations": "Existing reports have unresolved averaging windows/QA and do not prove factory causation. Annual averages and one-day reports are not a live feed.",
    },
    {
        "id": "historical_flood_event_inventories",
        "hazards": ["Flood", "Compound: cyclone + flood", "Compound: heavy rainfall + drainage failure"],
        "theme": "Historical event outcomes and impact evidence",
        "dataset": "India Flood Inventory v3 and INDOFLOODS event/gauge datasets",
        "publisher": "HydroSense Lab, IIT Delhi (IFI-Impacts); INDOFLOODS authors / Zenodo",
        "url": "https://zenodo.org/records/16994648",
        "resource_urls": [
            "https://zenodo.org/records/16994648/files/India_Flood_Inventory_v3.csv?download=1",
            "https://zenodo.org/records/14584655/files/floodevents_indofloods.csv?download=1",
            "https://zenodo.org/records/14584655/files/metadata_indofloods.csv?download=1",
            "https://zenodo.org/records/14584655/files/catchment_characteristics_indofloods.csv?download=1",
            "https://zenodo.org/records/14584655/files/precipitation_variables_indofloods.csv?download=1"
        ],
        "access": "Sources are catalogued in data/reference/public_data_sources.json and the existing public hydrology acquisition utility supports controlled downloads; check each licence and privacy/reuse field.",
        "priority": "P0",
        "status": "Acquired in workflow run 40928550082 and descriptively audited in a private 7-day artifact; raw data remain unvalidated and are not approved as Kochi training labels.",
        "required_checks": "Audit found 6,876 IFI event rows, 86 mentioning Ernakulam; INDOFLOODS has 4,548 events and 214 gauge records, including 26 Kerala gauges. Verify station/gauge identifiers, event dates, units, coordinate quality, privacy/licence fields, non-event sampling and leakage. Match stations only with a verified crosswalk.",
        "limitations": "District/event mentions do not establish ward-level or station-hour flood outcomes. INDOFLOODS has 155 Open and 59 Restricted gauge records; restricted records must be excluded from any shareable derived product. Candidate Kerala gauges include Periyar-area stations, but no station crosswalk or predictive labels have been approved."
    },
    {
        "id": "edayar_industrial_evidence",
        "hazards": ["Air pollution", "Industrial incident", "Compound: cyclone + flood"],
        "theme": "Industrial facility and regulatory evidence",
        "dataset": "Edayar candidate industry list, estate/allotment context, historic consent rows and dated air-quality reports",
        "publisher": "Kerala Water Authority; Directorate of Industries and Commerce, Government of Kerala; Kerala State Pollution Control Board",
        "url": "https://kwa.kerala.gov.in/wp-content/uploads/2022/11/Edayar_DER-1.pdf",
        "resource_urls": [
            "https://www.industry.kerala.gov.in/images/auto-cad/DA_EDAYAR.dwg",
            "https://industry.kerala.gov.in/images/DA-DP/Ernakulam/DA_Edayar.pdf"
        ],
        "access": "Project has a candidate facility table and linked evidence records under data/processed/industrial; CAD geometry has not been decoded into facility coordinates.",
        "priority": "P0",
        "status": "Candidate industry names, historical estate documents, some consent records and dated Eloor air-quality reports are acquired; verified facility points, current consent and measured air emissions remain unavailable.",
        "required_checks": "Verify current facility identity/occupancy, coordinates from authoritative geospatial evidence, current consent validity, permit limits, pollutant-specific measured emissions, monitoring station geometry, wind/time alignment and document reuse terms.",
        "limitations": "Eight facilities are a candidate list, not a complete active-facility inventory. Effluent records are not air emissions. Historical consent applications do not prove current authorization or factory-level pollution causation."
    },
    {
        "id": "ernakulam_health_facility_candidate_layer",
        "hazards": ["Flood", "Cyclone", "Earthquake", "Heatwave", "Industrial incident", "Compound: cyclone + flood"],
        "theme": "Critical-facility exposure",
        "dataset": "Ernakulam health-facility candidate GeoJSON",
        "publisher": "National hospital directory source; downloaded and filtered by existing project acquisition utility",
        "url": "https://ndhm.gov.in/",
        "priority": "P0",
        "status": "Downloaded in workflow run 40928550082: 642 point features, zero invalid points and zero district-filter mismatches; 64 duplicate-coordinate groups involve 213 records; only 84 points fell inside the provisional Kochi boundary candidate.",
        "access": "Short-lived private artifact only; existing spatial source metadata records the coordinate and reuse limitations.",
        "required_checks": "Resolve source coordinate order/CRS/datum/accuracy, duplicates, facility identity and current operation; verify the current official Kochi Corporation boundary before spatial joins.",
        "limitations": "Ernakulam district facilities are not all within Kochi Corporation. The 84/558 boundary split is preliminary screening against an unverified candidate boundary, not a facility error rate. No points are approved for raster exposure sampling."
    },
    {
        "id": "kochi_wards_2024_candidate",
        "hazards": ["Flood", "Cyclone", "Earthquake", "Heatwave", "Air pollution", "Industrial incident"],
        "theme": "Administrative boundaries",
        "dataset": "OpenCity Kochi Wards Map 2024 KML candidate",
        "publisher": "OpenCity.in catalogue; source attribution to Esri India Living Atlas",
        "url": "https://data.opencity.in/dataset/kochi-wards-map",
        "resource_urls": ["https://data.opencity.in/dataset/kochi-wards-map/resource/24a3de7a-4b14-436e-ae0c-e9ec7b1749e0"],
        "priority": "P1",
        "status": "Downloaded and structure-checked in workflow run 40928550082: 74 named placemarks, 74 unique names and 83 polygon geometries; legal/current delimitation alignment is unverified.",
        "access": "Short-lived private artifact only; candidate is not merged into the app's official boundary layer.",
        "required_checks": "Compare every ward name, ID, polygon and count against the current official KSMART/Delimitation Commission source; validate multipart features, topology, area and boundary date.",
        "limitations": "Structural validity does not prove legal currency. Do not use for ward-level risk/exposure claims or auto-correct spelling/name differences from geometry alone."
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
