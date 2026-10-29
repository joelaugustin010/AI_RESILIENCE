# Kochi consequence-model data requirements

**Status:** planning matrix; not a validated prediction model.  
**Scope:** flood, cyclone, earthquake, landslide, heatwave, drought, air pollution, industrial incidents, infrastructure failures, and compound hazards.

## Core principle

A consequence estimate requires more than a hazard record. For each scenario the project must connect:

1. **Hazard intensity and timing** — measured or modelled event conditions with units, spatial and temporal resolution, and provenance.
2. **Physical process data** — terrain, drainage, coastal boundary conditions, soil/geology, meteorology, networks, or other hazard-specific processes.
3. **Exposure** — current authoritative Kochi study boundary, geocoded people, buildings, facilities, and infrastructure.
4. **Vulnerability** — defensible information about how exposed assets respond to the hazard.
5. **Observed outcomes** — independently documented impacts and, where relevant, non-event periods for calibration and validation.
6. **Validation and uncertainty** — baseline comparison, event- or time-separated holdout evaluation, uncertainty, error analysis, and explicit intended-use boundaries.

The app's hazard-specific matrix is implemented in `src/consequence_data_requirements.py` and shown in the core decision workflow. It lists the input layers, candidate model family, current blockers, and likely authoritative starting sources for each supported hazard.

## Current acquisition streams

The public-data acquisition workflow now runs these streams independently where possible:

- Kerala rainfall and river-level observations through NWDP, with raw rows preserved and QA manifests.
- Historical flood-event inventories (IFI and INDOFLOODS) as incomplete event context—not ward-level flood truth.
- IMD/RSMC cyclone best-track history, with source flags retained and mirror provenance clearly disclosed.
- USGS ComCat regional earthquake catalogue, as regional seismicity context rather than local shaking/damage prediction.
- KSDMA flood raster and GSI landslide archive audits; the raster remains excluded until pixel meaning/licence are clarified, and the GSI polygons remain excluded because all three source geometries were invalid.
- Candidate Kochi ward and health-facility layers, not approved for asset-level exposure until authoritative identity, position, and boundary checks pass.
- Pinned official KSPCB annual AQI and Edayar source snapshots, acquired in a separate workflow step. Annual AQI summaries are not pollutant-specific hourly observations and cannot establish factory causation.

External raw datasets are stored in a short-lived private GitHub Actions artifact rather than committed to Git. This provides reproducible acquisition and checksums, not a permanent archive. Acquisition failures are reported separately and must not be interpreted as proof that a hazard or dataset does not exist.

## Hazard-specific minimum data

| Hazard | Required physical evidence | Exposure/vulnerability | Independent outcome evidence |
|---|---|---|---|
| Flood | Time-aligned rainfall, verified river stage/discharge datum, terrain, drainage, outfall/tide where relevant, observed extent/depth/duration | Current buildings, population, roads, hospitals, drainage and service networks; floor/elevation and fragility where available | Event-specific flood extent/depth/time, closures, damage, service disruption, plus defensible no-event periods |
| Cyclone | Official track/intensity, wind/rain fields, tide/surge/wave boundary conditions | Building type/condition, coastal elevation, shelters, roads, power/water dependencies | Event-linked wind/rain/surge, inundation, damage and outages |
| Earthquake | NCS + USGS catalogues, tectonic/geological context, ground-motion or hazard model | Local soil amplification and building/infrastructure fragility | Shaking/intensity, damage grades, outages and recovery linked to event |
| Landslide | Rainfall intensity-duration, terrain/slope, geology, soil and dated inventory | Roads, buildings, slopes and land-use changes | Validated event locations, runout/affected area and dated impacts |
| Heatwave | Temperature, humidity/heat metric, duration and night-time minima | Urban heat, shade/tree cover, outdoor exposure, age/health vulnerability, water/cooling access | Properly governed health/service outcomes and baselines |
| Drought | Rainfall anomaly, temperature/evaporative demand, soil moisture, reservoir/groundwater/flow | Water sources, storage, demand and distribution dependencies | Dated restrictions, source failure, groundwater stress and livelihood impacts |
| Air pollution | Pollutant-specific observations with timestamps, units, averaging periods, station coordinates and QA; meteorology | Population exposure, road/industry sources and verified emissions inventories | Quality-controlled pollution observations and suitable independent impact evidence |
| Industrial incident | Facility/process/substance-specific hazard, release/incident evidence and meteorology | Verified facility locations, population, drainage/transport pathways and response capacity | Confirmed incident, measured plume/contamination, evacuation and service impacts |
| Infrastructure failure | Asset condition, loading, failure history and network topology | Verified networks, redundancy, demand and backup duration | Time-stamped outages/closures and restoration |
| Compound hazards | Time-aligned inputs for each component and explicit dependence/coupling assumptions | Shared assets and cascading dependencies | Joint event/impact records; separate single-hazard histories do not establish joint probability |

## Release gates before numerical consequence estimates

- Source terms, attribution, retrieval date, checksum, units, time zone, CRS/datum, temporal/spatial coverage and limitations are recorded.
- Data are independently checked for duplicates/conflicts, missingness, geometry/coordinate validity, temporal gaps, and study-area overlap.
- The exposure layer is authoritative for the intended geography and current date.
- A physically or empirically defensible model is implemented for that hazard; inputs and assumptions are documented.
- Outcomes are independent of model inputs where possible, and test splits avoid event/time leakage.
- Results beat transparent baselines and report uncertainty, calibration, errors, known blind spots and intended use.
- A reviewer can reproduce the workflow from documented sources and versions.

**Until those gates pass, the app may support evidence review and clearly labelled hypothetical scenario comparison, but must not claim scientific prediction, exact factory attribution, official warnings, or verified asset-level exposure.**
