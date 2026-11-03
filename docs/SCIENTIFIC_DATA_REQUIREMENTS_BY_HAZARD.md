# Scientific data requirements by hazard

**Review basis:** Existing repository files and source registers, plus official
source-page checks recorded in this review. This is a data-readiness review,
not a new prediction-model phase. No datasets were downloaded or promoted in
this review.

## Status definitions

These statuses describe whether a requirement is supported by an inspected
local asset for the stated use; they do not rate a publisher in general.

- `AVAILABLE_AND_SUITABLE`: acquired, traceable, quality-described, and fit
  for the specific use and scale.
- `AVAILABLE_WITH_LIMITATIONS`: an inspected asset exists, but material
  limitations restrict the use or interpretation.
- `AVAILABLE_BUT_NOT_SUITABLE`: an asset or source artifact exists, but it
  cannot support the stated use.
- `REQUIRES_OFFICIAL_ACCESS`: a known official source requires an account,
  provider confirmation, or formal access/permission not available here.
- `NOT_FOUND`: no suitable local asset or verified accessible extract was
  found. A source lead may still exist.

“Calibration” below means fitting or calibrating a hazard/consequence method
against suitable local measurements or outcomes. “Independent validation”
means comparison to outcomes not used in fitting, with event/time/geographic
separation as appropriate. Dataset byte/hash checks do not establish either.

## Common spatial and outcome foundation

| Requirement | Purpose; expected variables and units | Minimum useful temporal/spatial support | Actual local evidence and status | Calibration / independent validation |
|---|---|---|---|---|
| Terrain, elevation, slope, flow direction, catchments | Elevation (m, stated vertical datum); slope (degrees or %); hydrologically conditioned flow paths | DEM fine enough for urban drainage and asset-scale questions; local catchments/outfalls with surveyed control | No verified local DEM, vertical datum, catchment, or drainage model. Candidate GSI/terrain sources are not acquired and validated. `NOT_FOUND` | Neither available |
| Land cover, imperviousness, soil, infiltration | Class, impervious fraction (%), soil texture/infiltration (documented units) | Current, local raster/vector resolution appropriate to subcatchments; dates spanning analysis period | No verified local layer suitable for runoff or landslide parameterization. `NOT_FOUND` | Neither available |
| Administrative geography | Legal/current boundary and stable IDs; CRS and accuracy | Current boundary/ward scale with publication date and topology QA | One provisional Kochi polygon has a self-intersection; community-repackaged ward layer has exclusions/missing identifiers and is not authoritative. `AVAILABLE_BUT_NOT_SUITABLE` for exposure accounting | Neither available |
| Population and vulnerability | Population counts/density (persons); age, disability, socioeconomic or occupancy attributes with definitions and privacy controls | Current census/reference period; ward/grid resolution compatible with hazard footprints | No compatible verified Kochi population/vulnerable-group layer found. `NOT_FOUND` | Neither available |
| Asset inventory and service dependencies | Verified locations, use/status, capacity, condition, fragility, dependency edges | Owner-confirmed coordinates/CRS, update date, facility/segment scale | NIHFW directory is review-only; OSM road ways are context only; drainage, utilities, capacities, condition, and dependency networks are absent. `AVAILABLE_BUT_NOT_SUITABLE` for consequence exposure | Neither available |
| Event/outcome registry | Event ID, onset/end/timezone, observed hazard footprint/intensity, affected/damaged assets, people, losses and service interruption | Independently sourced event records with compatible geographies and dates | No reviewed local event-by-location impact registry or non-event comparison set. `NOT_FOUND` | No hazard-specific consequence calibration or independent validation |

## 1. Flood

| Variable / evidence | Purpose and units | Required support | Actual evidence and status | Calibration / validation and gap |
|---|---|---|---|---|
| Rainfall history/forcing | Gauge or grid precipitation (mm per stated interval); event hyetograph and IDF (mm/h versus duration/return period) | Sub-hourly to hourly event series; local station/catchment coverage and long homogeneous record for IDF | NWDP manual rainfall: 21 stations, 2000-02-27–2014-12-31, hourly, filename says 1991–2020; source-hash matched but temporal coverage incomplete. CWC telemetry: 4 stations, 2021–2025 with 324 conflicting duplicate groups. IMD 0.25° grids only 2018/2021/2024; NASA POWER is a gridded point series. `AVAILABLE_WITH_LIMITATIONS` | No local flood-outcome calibration/validation. Resolve station identity, conflicts, timezone, QC and obtain continuous local IDF-quality record. |
| River stage/discharge | Stage (m relative to documented gauge datum), discharge (m³/s), threshold and rating curve | Sub-hourly/hourly synchronized upstream/downstream gauges; catchment context | NWDP manual/telemetry records exist for 6 stations (2022–2025 / 2021–2025), but datum, station semantics and operational thresholds are unresolved. No verified discharge/rating curves. `AVAILABLE_WITH_LIMITATIONS` | No event-linked flood outcomes; cannot compare raw stage values to unverified danger thresholds. |
| Inundation extent/depth/duration | Observed event footprint; depth (m); start/end or duration (h) | Dated event imagery/survey with CRS, vertical reference, NoData and event ID; urban-scale resolution | JRC GloFAS RP100 is modeled river-flood scenario context; KSDMA Ernakulam archive exists but pixel meaning, NoData and reuse are unresolved. No verified observed local event footprints/depths. `AVAILABLE_BUT_NOT_SUITABLE` for observed outcomes | No calibration or independent flood validation. Obtain event-specific observed extent/depth and independent reference outcomes. |
| Drainage and catchment response | Catchment area (ha/km²), time of concentration (h), drainage geometry/capacity (m³/s), blockage/storage/outfall state | Surveyed asset/catchment-level network and event-time operating state | No verified drainage, outfall, capacity, blockage, or catchment layer. User-entered scenario inputs are not measured infrastructure data. `NOT_FOUND` | No calibration or validation. |
| Exposure and impacts | People/facilities/roads in footprint; damage, displacement, service interruption, loss | Current geocoded assets/population, compatible with observed flood depth/duration | No verified population, asset, vulnerability or flood impact registry; hospital coordinates are not spatially validated. `NOT_FOUND` | No calibration or independent validation. |

## 2. Cyclone

| Variable / evidence | Purpose and units | Required support | Actual evidence and status | Calibration / validation and gap |
|---|---|---|---|---|
| Track and storm structure | Best-track position (lat/lon), time (UTC), intensity, central pressure (hPa), wind radii | Event-level track with agency conventions and uncertainty; regional approach history | NOAA NCEI IBTrACS v4r01 documented, but all-storm CSV was not downloaded; a Kochi-relevant extract is not local. `NOT_FOUND` (source catalogued, not acquired) | No local impact calibration/validation; obtain and document authorized extract. |
| Local wind and pressure | Sustained/gust wind (m/s or km/h), pressure (hPa), duration | Quality-controlled observations at exposed locations and event time | No verified local event-time wind/pressure series; NASA POWER daily gridded wind is not gust data. `NOT_FOUND` for event intensity | Neither available |
| Rainfall, river, coast | Rain (mm/interval), river stage (m/datum), tide/surge/water level (m/vertical datum) | Synchronized sub-hourly event data, coastal gauge and hydrologic boundaries | Rain/river assets have the limitations above; no verified surge/tide gauge or local cyclone event linkage. `AVAILABLE_WITH_LIMITATIONS` for partial rain/river only; `NOT_FOUND` for coast | No compound calibration/validation |
| Built environment and impacts | Building class/height/roof/condition/occupancy; damage and outage outcomes | Geocoded inventory and event-linked, independently assessed damage | No verified building inventory, fragility or cyclone damage registry. `NOT_FOUND` | Neither available |

## 3. Earthquake

| Variable / evidence | Purpose and units | Required support | Actual evidence and status | Calibration / validation and gap |
|---|---|---|---|---|
| Earthquake catalogue | Origin time, coordinates, depth (km), magnitude type/value, uncertainty, completeness | Reviewed regional catalog with agency metadata and completeness/magnitude thresholds | USGS query for 1900–2026 and a broad Kerala bounding box returned zero features; that response is not a completeness statement. NCS portal is official, but a suitable local extract was not acquired. `AVAILABLE_BUT_NOT_SUITABLE` | No local event/outcome calibration or independent validation |
| Ground motion and site conditions | PGA/PGV (g or m/s), response spectra, site class, geology/soil | Site-specific or validated regional hazard/shaking products with documented return period and CRS | No verified Kochi site-class, local ground-motion, or applicable geotechnical layer. `NOT_FOUND` | Neither available |
| Buildings, occupancy, damage | Structural typology, age, material, height, occupancy; observed damage/injuries | Geocoded current inventory and event-level independent damage assessment | No verified building fragility/inventory or local earthquake impact records. `NOT_FOUND` | Neither available; earthquake occurrence data alone cannot establish local vulnerability. |

## 4. Landslide

| Variable / evidence | Purpose and units | Required support | Actual evidence and status | Calibration / validation and gap |
|---|---|---|---|---|
| Terrain and geology | Elevation (m/datum), slope (degrees), curvature, lithology, faults, soil depth | Fine-resolution DEM/geology with scale, date, CRS and local coverage | No verified local analysis-ready terrain/geology. GSI Ernakulam 2022 susceptibility layer is catalogued but linked ZIP was not retrievable/validated. `NOT_FOUND` for usable inputs; the failed source retrieval is not evidence that access is restricted. | Neither available |
| Triggering rainfall and saturation | Rainfall intensity (mm/h), event duration, antecedent totals (mm), soil moisture (m³/m³ or % with definition) | Sub-hourly/daily continuous records and local failure-linked windows; soil-moisture coverage | Rainfall files are partial/conflicted; no local measured soil moisture. `AVAILABLE_WITH_LIMITATIONS` for rainfall only; `NOT_FOUND` for soil moisture | No locally calibrated intensity-duration/antecedent threshold or validation |
| Failure inventory and exposure | Failure location/date/type/volume; people/assets affected and damage | Georeferenced, dated inventory with non-failure sampling and reporting completeness | No verified Ernakulam failure inventory/outcome registry. `NOT_FOUND` | Neither available |

## 5. Heatwave

| Variable / evidence | Purpose and units | Required support | Actual evidence and status | Calibration / validation and gap |
|---|---|---|---|---|
| Thermal and meteorological forcing | Air temperature (°C), relative humidity (%), wind (m/s), radiation (W/m²), duration | Hourly, quality-controlled station/grid data with uncertainty and local coverage | NASA POWER daily precipitation/temperature/10-m wind at a point is gridded/model-derived; it does not supply a verified hourly local heat-stress series or complete variables. `AVAILABLE_BUT_NOT_SUITABLE` for local hourly heat-health prediction | No calibration/validation |
| Alerts and health criteria | Locally applicable threshold, acclimatization, alert duration and issuing authority | Current official Kerala/IMD guidance and defined geographic/time basis | Existing model documentation includes a US NWS heat-index screening method; it is not a Kerala health threshold. No verified local criteria incorporated as outcome labels. `AVAILABLE_BUT_NOT_SUITABLE` | No local calibration/validation |
| Exposure, health and service outcomes | Population/age/occupation/health vulnerability; heat illness, mortality, electricity/water demand/outages | Privacy-safe, time/location-resolved health and service records linked to heat events | No verified local population-vulnerability or heat outcome series. `NOT_FOUND` | Neither available |

## 6. Drought

| Variable / evidence | Purpose and units | Required support | Actual evidence and status | Calibration / validation and gap |
|---|---|---|---|---|
| Long-term precipitation baseline | Monthly precipitation (mm); SPI requires a suitable homogeneous reference series (at least 30 years for intended baseline) | Continuous monthly series per homogeneous location; documented missingness and station changes | Manual rainfall is hourly 2000–2014; IMD acquired years are only 2018, 2021, 2024; POWER is 2020–2025. None is a continuous local 30-year monthly reference. `AVAILABLE_BUT_NOT_SUITABLE` | No defensible local SPI baseline calibration or independent validation |
| Water balance and storage | Evapotranspiration (mm), soil moisture (m³/m³), streamflow/storage (m³ or m³/s), groundwater level (m/datum), demand | Monthly/daily coverage tied to basin, reservoir, aquifer and user sectors | No verified local water-resource/storage/demand or agricultural soil-moisture series. `NOT_FOUND` | Neither available |
| Drought impacts | Crop/vegetation condition, water supply restrictions, ecological and economic outcomes | Georeferenced seasonal outcomes and non-event baselines | No reviewed local drought impact registry. `NOT_FOUND` | Neither available |

## 7. Industrial incident

| Variable / evidence | Purpose and units | Required support | Actual evidence and status | Calibration / validation and gap |
|---|---|---|---|---|
| Facility and process inventory | Verified coordinates/CRS, process, substances, inventory (kg), operating status, storage and safety barriers | Current owner/regulator records, facility-scale coordinates, date and reuse permission | KSPCB consent/industrial documents and Edayar allotment records exist, but do not verify current emissions, inventories, operating state or spatially usable locations. KSDMA industrial hazard map is static PDF only. `AVAILABLE_BUT_NOT_SUITABLE` | No incident model calibration/validation |
| Release and dispersion inputs | Substance, released mass/rate (kg/s), duration, temperature, release height, wind/stability/terrain | Incident-specific or permitted process/emissions data and meteorology at matching time/resolution | No verified release measurements or source-specific emissions; daily NASA POWER is not incident-time dispersion meteorology. `NOT_FOUND` | Neither available |
| Monitoring and health/environment outcomes | Pollutant-specific concentration (µg/m³, ppm), sampling method/QC, coordinates, time; exposure and incident impacts | Co-located/upwind-downwind quality-controlled series with event and source records | KSPCB AQI summaries/reports exist but are not a complete pollutant-specific series; no suitable CPCB/KSPCB station geometry/time series verified. `AVAILABLE_WITH_LIMITATIONS` for AQI context; `NOT_FOUND` for source-attribution evidence | No source-attribution calibration or independent validation; AQI/proximity cannot prove cause. |

## 8. Infrastructure failure

| Variable / evidence | Purpose and units | Required support | Actual evidence and status | Calibration / validation and gap |
|---|---|---|---|---|
| Asset/network topology | Verified road, bridge, drainage, power, water, telecom, hospital and emergency-facility nodes/edges; capacity and redundancy | Owner-confirmed GIS, stable IDs, CRS, update date and dependency/service relationships | OSM road geometry exists as a provisional snapshot (16,378 highway ways) but not authoritative, complete, condition-coded, or passability-verified. Hospital directory is not spatially validated; LRIS road/drainage candidates not ingested. `AVAILABLE_BUT_NOT_SUITABLE` | No network calibration or validation |
| Condition, failure and restoration | Failure mode, condition rating, capacity, outage start/end, repair time, service area | Asset-owner inspection and outage/maintenance history with incident timestamps | No verified local failure, outage, capacity, maintenance or restoration dataset. `NOT_FOUND` | Neither available |
| Dependencies and consequences | Service-to-asset dependencies, demand served, population/economic exposure, observed cascading effects | Explicit owner-verified edges and time-resolved event outcomes | No verified dependency graph, population service areas or cascade outcomes. `NOT_FOUND` | Neither available; conceptual dependencies are not evidence of actual vulnerability. |

## 9. Compound: cyclone + flood

| Variable / evidence | Purpose and units | Required support | Actual evidence and status | Calibration / validation and gap |
|---|---|---|---|---|
| Cyclone forcing and timing | Track, wind/gust (m/s), pressure (hPa), rainfall (mm/interval), event time | Synchronized event-specific track and local meteorological observations | IBTrACS documented but no local extract; partial rainfall series have gaps/conflicts. `AVAILABLE_WITH_LIMITATIONS` for rainfall; `NOT_FOUND` for local storm forcing | No event-linked calibration/validation |
| Coastal/river boundary interaction | Tide/surge/river stage (m with vertical datum), discharge and drainage outfall/backwater conditions | Synchronized coastal and inland gauges with datum, geometry and operating state | River levels exist with unresolved datum; no acquired tide/surge/outfall/drainage measurements. `AVAILABLE_WITH_LIMITATIONS` for river series; `NOT_FOUND` for coastal/drainage dependencies | Interaction is unresolved; no calibration/validation |
| Compound footprints and impacts | Observed flood extent/depth/duration, population/assets/services affected, event attribution/timeline | Common geospatial/time reference and independent event outcome evidence | JRC RP100 is modeled context; KSDMA interpretation is unresolved; no verified compound event outcomes or exposed asset layers. `AVAILABLE_BUT_NOT_SUITABLE` | Neither available |

## 10. Compound: heavy rainfall + drainage failure

| Variable / evidence | Purpose and units | Required support | Actual evidence and status | Calibration / validation and gap |
|---|---|---|---|---|
| Rainfall forcing | Observed/design intensity (mm/h), duration, temporal distribution and return-period basis | Local sub-hourly gauges/IDF and event records with quality flags | NWDP and IMD evidence is incomplete/conflicted/coarse; no verified local design hyetograph/IDF. `AVAILABLE_WITH_LIMITATIONS` | No drainage event calibration or independent validation |
| Drainage system state | Catchment area (ha), runoff coefficient (dimensionless, sourced), time of concentration (h), capacity (m³/s), storage/outfall/tide/backwater/blockage | Surveyed subcatchment and asset network with measured capacities and time-varying condition | No verified drainage/catchment/outfall network or capacity inventory. User-entered values only define illustrative scenarios. `NOT_FOUND` | No local calibration/validation |
| Observed urban flooding and consequences | Inundation location/depth/duration; affected people/buildings/roads/services and damage | Event-specific independent observations and current geocoded exposure | No verified event footprint, population/asset exposure or impacts. `NOT_FOUND` | Neither available |

## Acquisition and next data gates

Official source leads were checked but not represented as downloads:

- IMD describes a 0.25-degree daily rainfall product for 1901–2024 and cautions
  that it cannot guarantee correctness in all circumstances; local files in
  this repository cover only 2018, 2021 and 2024.
- NASA GPM IMERG documentation describes satellite precipitation products;
  no authorized Kochi extract was acquired in this review.
- NOAA IBTrACS v4r01 has current technical documentation and a user
  registration request; no regional file was acquired.
- NCS is an official earthquake source, but no completeness-described local
  catalogue was acquired. The GSI Bhukosh endpoint failed retrieval.
- Kerala LRIS was not reachable during source check; no road/drainage export
  was acquired. KSDMA's hazard-map page documents district flood products,
  including Ernakulam PDFs, but the existing raster's semantics and reuse
  remain unresolved.
- CPCB/KSPCB monitoring and asset-owner datasets still need provider-defined
  schemas, QA/QC, spatial metadata, and reuse permissions.

Before any consequence estimate is enabled, acquire and verify (1) continuous
hazard observations with station/measurement metadata; (2) suitable event
footprints and independent observed outcomes; (3) current owner-confirmed
population and asset layers; (4) terrain, drainage, coastal and infrastructure
dependency data where relevant; and (5) reuse terms. Record event IDs,
timestamps/timezones, CRS/datums, units, missingness, duplicate/conflict
resolution, and independent validation splits. Until these are available, keep
the corresponding outputs at `INSUFFICIENT EVIDENCE FOR A RELIABLE ESTIMATE`.
