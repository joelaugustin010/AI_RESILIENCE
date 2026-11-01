# Data gaps and requirements for consequence prediction

**Review date:** 2026-11-02
**Data policy:** Existing repository data were inspected; no new records are
inferred from URLs, illustrative files, or unverified coordinates. Local
predictions must remain disabled until evidence is fit for the specific model.

The expanded variable-by-variable inventory for all ten existing selections
is in [SCIENTIFIC_DATA_REQUIREMENTS_BY_HAZARD.md](./SCIENTIFIC_DATA_REQUIREMENTS_BY_HAZARD.md);
the domain-level sufficiency assessment is in
[KOCHI_SCIENTIFIC_DATA_READINESS_MATRIX.md](./KOCHI_SCIENTIFIC_DATA_READINESS_MATRIX.md).
These documents record repository acquisition status separately from source
leads and distinguish model inputs from calibration/training and independent
validation outcomes.

## Shared high-priority requirements

| Requirement | Why it is needed | Current project condition | Acceptance before integration |
|---|---|---|---|
| Independent event/outcome registry | Labels for testing hazard and consequence estimates. | No reviewed event-by-location impact registry. KSDMA PDFs provide return-period/modelled hazard context, not independent event outcomes. | Publisher, event definition, time basis, geometry, outcome definition, independent review, provenance/hash and non-event cases. |
| Local hazard footprints and intensity | Spatially identify the footprint/intensity affecting people and assets. | JRC modeled RP100 and KSDMA Kochi Taluk return-probability PDFs exist; KSDMA raster semantics/reuse remain unresolved. No validated dated observed flood extent/depth/duration was found. | Authoritative source, documented units/CRS/NoData, date/event, resolution, uncertainty and independent geometry/value QA. |
| Current population and vulnerable-group data | Estimate exposed population or health-service requirements. | A WorldPop 2025 modeled/constrained 100 m India grid covers Kochi, but it is not census/household data; its dataset-specific reuse terms and local accuracy remain unresolved. No vulnerable-group layer. | Geographic/time resolution, population definitions, reference date, privacy protection, reuse rights and validation against local totals. |
| Terrain and land cover | Support hydrological/terrain context and land-cover description. | Copernicus GLO-30 DSM and ESA WorldCover 2021 tile cover the reference point. DSM vertical reference/hydrologic conditioning and land-cover fit for imperviousness remain unverified. | Surveyed or accuracy-described bare-earth terrain, datum, locally suitable resolution; current land-cover/imperviousness with documented classes and validation. |
| Owner-confirmed asset locations and attributes | Estimate facility exposure, fragility and service interruption. | NIHFW hospital coordinates are review-only; road snapshot is not a verified passability/network layer; utilities/drainage absent. | Responsible owner confirmation, CRS/order/accuracy, asset status/capacity/condition, update date and compatible hazard data. |
| Time synchronization and station metadata | Relate hazard observations to impact windows without leakage. | NWDP station IDs/coordinates, source time zone and some measurement semantics unresolved; rainfall conflicts exist. | Provider-confirmed station metadata, time zone, sampling/QC flags, gauge datum/threshold where relevant, and conflict resolution. |
| Licences and reuse terms | Establish permitted redistribution and application use. | Several acquired products have uncertain dataset-specific terms; KSDMA and some IMD/derived product reuse need confirmation. | Retain authoritative licence statement and attribution; do not make a restricted product public or bundle it for deployment. |
| Independent validation coverage | Quantify generalization and operational error. | Only a retrospective single-split rainfall measurement benchmark; no disaster consequence validation. | Chronological/event/geographic holdout, predeclared baselines, adequate independent cases, uncertainty and expert review. |

## Hazard-specific input requirements

| Selection | Essential additional data for consequence estimates | Current blocker |
|---|---|---|
| Flood | Local design rainfall hyetographs/IDF; catchments; surveyed terrain; drainage topology, capacity, condition and outfalls; river and tide boundaries; event footprints/depth/duration; affected-population and asset layers; independent damage/service outcomes. | Current runoff is a catchment scenario only. No validated hydraulic/inundation or consequence dataset. |
| Cyclone | IMD track/advisories and local gust/duration/pressure; coastal surge/tide; rainfall/river observations; building class/condition/occupancy; asset fragility and event damage. | NOAA IBTrACS v4r01 North Indian CSV is acquired and structurally validated (62,891 rows; 1842–2026; 500 points from 69 storm IDs within a 300 km QA radius of Kochi). Dataset-level reuse terms are unresolved, so it is not integrated. No local wind, surge, fragility, or impact linkage. |
| Earthquake | Reviewed NCS/GSI/USGS event catalogue; site class/soil; ground motion; building inventory and structural fragility; occupancy and event damage. | USGS query returned zero records; no local shaking or building evidence. |
| Landslide | High-resolution terrain, geology, soil, land cover, drainage/saturation; dated georeferenced failure inventory; station rainfall and local intensity-duration/antecedent calibration; impact records. | No suitable local failure inventory, calibrated threshold or validated footprint. |
| Heatwave | Quality-controlled hourly temperature, humidity, radiation and wind; locally adopted alert criteria; population vulnerability/occupancy; heat-health and service outcome records. | Heat-index scenario only; no local forecast or health outcomes. |
| Drought | At least 30 consecutive quality-controlled monthly rainfall years per homogeneous location for SPI; water balance/evapotranspiration; source/reservoir/storage and demand; agriculture/ecosystem/service outcomes. | Existing manual local copy spans 2000-2014 and is incomplete; current years are non-contiguous. |
| Industrial incident | Pollutant-specific QA monitoring; current source emissions/process/stack/operating records; meteorology, terrain and release parameters; source apportionment; time/location exposure and independently reviewed impacts. | AQI and permit records do not establish release/source, plume, exposure or cause. |
| Infrastructure failure | Owner-verified asset GIS, dependency topology, capacities/redundancy, condition, failure/outage/repair/service records and hazard-specific vulnerability. | Conceptual links and OSM context only; no validated service network. |
| Cyclone + flood | Synchronized track/wind/rain, river/coastal water/tide, drainage state, compatible flood footprints, service/asset/population exposure and impact timeline. | No common event-time/spatial dataset; interaction unresolved. |
| Heavy rainfall + drainage failure | Local IDF/design hyetograph and time of concentration, verified subcatchment/imperviousness, surveyed drainage/capacity/storage/outfalls, tide/backwater/blockage state, observed inundation and impacts. | Current equation uses scenario inputs; cannot locate actual surcharge or estimate damage. |

## Existing spatial file checks

- The provisional Kochi Corporation boundary has one polygon but fails local
  validation due to a self-intersection. It is not a verified analysis mask.
- The community-repackaged ward layer has 74 processed polygons passing the
  repository's local geometry check. Three source polygons were excluded for
  invalid geometry and six source rows lack ward identifiers. It is not a
  current/legal hazard boundary.
- NIHFW Ernakulam review contains 180 rows, 31 missing/nonnumeric coordinate
  pairs and 18 repeated coordinate-pair groups covering 63 rows. Coordinate
  order, CRS/datum and per-record accuracy are unresolved. Do not sample flood
  rasters at these points.
- New GSI Ernakulam landslide ZIP has one EPSG:32643 polygon layer with 3
  features. Transformed bounds 76.4091–76.9215 E do not intersect the
  approximate Kochi review bounds; class semantics and topology remain
  unverified.
- New Copernicus DSM tile and WorldCover tile contain the Kochi reference
  point. The former lacks confirmed local vertical reference/survey accuracy;
  the latter is 2021 land-cover classification, not building footprints or
  validated imperviousness.
- New WorldPop 2025 raster covers Kochi at nominal 100 m, but it is a
  modelled estimate, not census/household data. The local 100 x 100 sample
  window contains 4,646 NoData cells; NoData is not zero population.
- KSDMA raster value/NoData semantics and reuse terms are unresolved.
- KSDMA Ernakulam PDF contains Kochi Taluk maps for 10–500-year return
  probability, with map water-level classes; page labels say boundaries are
  unverified/reference-only. This is not a dated observed flood footprint or
  validated outcome.
- No validated drainage, utility, hospital/road passability or event-linked
  population exposure layer is available for spatial consequences.

## Data acquisition status

Eight additional originals were downloaded and structurally inspected on
2026-11-02; details, SHA-256 values, source URLs, licenses, and suitability
are recorded in [DATA_ACQUISITION_REPORT.md](./DATA_ACQUISITION_REPORT.md),
[DATA_SOURCES.md](./DATA_SOURCES.md), sidecars under
`data/raw/experimental/kochidata_2026-11-02/`, and
`data/reference/DATA_PROVENANCE_REGISTER.json`. No new file was integrated
into the application. Official source checks for NASA GPM IMERG, NOAA
IBTrACS, NCS, GSI Bhukosh, Kerala LRIS, CPCB/KSPCB and owner-managed networks
identified account, provider, metadata, or licence blockers; these are not
relabelled as acquired data.

### Exact external access requests required

| Responsible authority / owner | Dataset and exact request needed | Why a public web page or existing file is insufficient |
|---|---|---|
| KSDMA / Kerala State Emergency Operations Centre and Ernakulam DDMA | Machine-readable event-specific flood footprints, depth/duration observations, event IDs and timelines; the KSDMA 2022 historic/RCP8.5 report methodology and underlying raster/vector layer; pixel values/NoData, CRS, update period, class definitions, and written reuse/deployment permission for the report/map files. | Existing PDFs are scenario/return-probability reference products; map boundaries are explicitly unverified, and no dataset-specific reuse terms were found. |
| Kerala Water Resources Department / Kerala Surface Water Department and CWC/NWIC | Station coordinates/IDs, measurement QC, timestamp timezone, river gauge datum/zero, rating curves/discharge, warning thresholds; resolve the 324 conflicting CWC rainfall station-time groups; formal data-use terms. | Current NWDP files have incomplete/contradictory coverage and unresolved metadata; river levels cannot be interpreted as absolute elevation or compared with unverified thresholds. |
| Kochi Municipal Corporation Engineering/Storm Water Drainage section; Kerala Land Use Department / LRIS | Current GIS of storm drains, canals, outfalls, catchments, invert/asset elevations, capacities, condition, blockage/storage and survey date; schema/CRS/accuracy and written reuse permission. | No downloadable, documented city drainage/capacity network was verified; natural waterways are not a substitute for storm drains. |
| WorldPop | Written confirmation of the dataset-specific licence/reuse conditions for `ind_pop_2025_CN_100m_R2025A_v1.tif`; guidance on constraints/NoData and validation against authorized current local totals. | Public download and summary existence do not establish dataset-specific redistribution rights or city-scale accuracy. |
| Census of India / Kerala Directorate of Census Operations and Kochi Municipal Corporation | Current authorized population/household counts, enumeration/ward boundaries, household/building inventory, reference date, stable IDs, CRS/accuracy and use permission. | WorldPop is modelled population-per-cell, not household/census data; local legal ward boundaries are not validated. |
| Kerala Health Department / NIHFW; Education Department / UDISE+; Kerala PWD / NHAI; KSEB; Kerala Water Authority; Kochi Corporation emergency services | Owner-confirmed, current GIS for operating hospitals, schools, roads/bridges, power/water assets, emergency facilities, capacities, condition, service areas and dependency/outage records; coordinate metadata, update date and written reuse permission. | Existing hospital points are unverified, OSM is community-mapped context, and no utility/bridge/dependency network is available. |
| CPCB and KSPCB | Quality-controlled pollutant-specific observations with units, station coordinates/CRS, timestamps/QC, sampling metadata; current facility emissions/process/releases and formal data reuse/access terms. | AQI summaries and consent orders do not establish source-specific pollutant levels, releases, exposure, or causation. |
| WorldPop / local academic or government data custodians | Independent local validation references and appropriate geographies for any modeled population grid; no personal records are requested. | No local calibration/validation totals or event-specific exposed-population outcomes are available. |

### Safe integration gate

1. Confirm official publisher, source URL, licence and retrieval/publication
   dates.
2. Hash and preserve the source asset; maintain its metadata and transformations.
3. Validate schema, units, timestamps/time zone, CRS, bounds, geometry, missing
   values, duplicate/conflict groups and coverage.
4. Confirm the dataset resolves the specific model input at appropriate
   spatial/temporal resolution.
5. Match to independent outcomes and document validation before enabling a
   local consequence estimate.
6. If any gate fails, show `INSUFFICIENT EVIDENCE FOR A RELIABLE ESTIMATE`;
   never treat missing data as zero impact.

## Follow-up acquisition status (2026-11-02)

- Census of India 2011 Ernakulam District Census Handbook Parts A/B and the
  associated Kerala town/village directory workbooks were downloaded from
  the official Census Digital Library. They provide historical population,
  household, and aggregated service/amenity context, but no current local
  geometry. Explicit redistribution terms and the necessary official
  town-part/ward crosswalk remain unresolved; do not use these data as
  present-day exposure.
- Kerala LRIS 2.0 publicly advertises Ernakulam drains, roads, waterbodies,
  and watersheds as WMS layers with EPSG:4326 bounds intersecting the
  approximate Kochi-area review bounds. The WFS service is disabled, so no
  raw features were downloadable. The WMS metadata does not establish
  municipal coverage, data currency, layer meaning, capacity, completeness,
  or reuse rights.
- No dated observed Kochi flood footprint/depth/duration, drainage
  capacity/outfall records, current building/household data, owner-verified
  facility/utility GIS, or event-linked casualty/displacement/damage/loss
  file was acquired in this follow-up.
- NOAA IBTrACS v4r01 was downloaded from the NCEI North Indian Ocean CSV
  endpoint and validated, but its NCEI product page and DOI metadata did not
  establish dataset-specific reuse terms. The original is retained locally
  only; obtain written NCEI clarification before distributing or integrating
  track geometry. A best-track archive is not a local wind or impact registry.

**Next acquisition requests:** ask LRIS/Land Use Department for
WFS/GeoPackage downloads, layer metadata, survey/update date, and reuse
permission for drains, waterbodies, watersheds, and roads; request Kochi
Corporation/Kerala Irrigation/CWC records for storm-drain assets, capacity,
outfalls, gauge datum and dated flood observations; request KSDMA event
impact records with event identifiers/geography; request current Census/
LSGD population/building and line-department facility/utility extracts with
official spatial crosswalks and explicit redistribution terms. For cyclone
tracks, request written reuse/redistribution terms from NOAA NCEI for
IBTrACS v04r01, then review only Kochi-relevant observations against
independently recorded local wind, surge and impact records.
