# Phase 4 scientific model selection

**Review date:** 2026-11-02  
**Project focus:** Kochi and Ernakulam  
**Decision rule:** select a method from the physical process and verified
inputs available. A computable value is not, by itself, a prediction.

## Ten-disaster model-selection matrix

| Existing workflow selection | Selected approach and governing principle | Project data usable now | Essential missing evidence | Current output and scientific boundary |
|---|---|---|---|---|
| Flood | Rainfall descriptor and conditional Rational Method screening, `Q = 0.00278 C i A` for mean intensity in mm/h and area in hectares. A separate one-hour rainfall-measurement backtest is available; it does not predict flooding. | Manual hourly rainfall source records (observed timestamps 2000-02-27 through 2014-12-31) support a retrospective, statewide station-value benchmark. IMD 0.25-degree grids, CWC telemetry, river records and JRC RP100 tiles are visible as context with documented limitations. | Verified local rainfall IDF/design hyetograph, catchments, terrain, drainage topology/capacity/condition, river gauge datum and thresholds, tide/backwater data, event flood footprints/depths and independently reviewed impacts. | Scenario runoff indicator only; no inundation extent, depth, return period, probability, or flood consequence prediction. Rainfall backtest status is `HISTORICAL RECONSTRUCTION`, not an operational forecast. |
| Cyclone | Wind-speed conversion and idealized dynamic pressure, `q = 0.5 rho v^2`; track, surge, rainfall and damage are not inferred. | NASA POWER daily gridded/model-derived meteorology is broad context only. No official event forecast or local event wind series is joined. | Official time-stamped IMD track/advisories, quality-controlled local gust/sustained wind and pressure, coastal water/surge, rainfall, terrain/exposure and building fragility. | User-input physical indicator only. No track forecast, local warning, wind-load, damage or exposed-facility prediction. |
| Earthquake | Review of optional reported Modified Mercalli Intensity (MMI), an ordinal description of observed effects; no magnitude-to-damage conversion. | USGS regional query response is preserved; its query returned zero records and is not a complete seismicity assessment. | Reviewed NCS/GSI/USGS event and hazard information, site class/ground-motion observations, geotechnical conditions, building inventory/fragility and independent outcomes. | Reported MMI context only. No earthquake likelihood, site shaking, structural damage or exposure prediction. |
| Landslide | Rainfall intensity-duration context; no empirical trigger threshold is transferred without local calibration. | IMD grid years and NWDP rainfall records can show limited context; station/time conflicts and incomplete/local matching prevent a validated threshold analysis. | High-resolution terrain, geology, soils, land cover, drainage and saturation; georeferenced local failure inventory; time-matched quality-controlled rainfall and independently reviewed trigger outcomes. | Mean rainfall descriptor only; no susceptibility map, trigger class, time-to-failure or affected-location estimate. |
| Heatwave | NOAA/NWS Rothfusz heat-index regression within its published domain; screening bands are not Kerala warning thresholds or medical triage. | User-entered temperature and humidity can be assessed as a scenario. NASA POWER daily values are not co-located observations for an assessed event. | Quality-controlled hourly local temperature, humidity, radiation and wind; locally adopted warning/action criteria; population vulnerability and independent health outcomes. | Apparent-temperature screening only when inputs meet method domain; no forecast horizon, local heat warning, health demand or casualty estimate. |
| Drought | Station-level one-month Standardized Precipitation Index (SPI-1), calendar-month gamma fit with zero adjustment, requiring a complete same-location monthly climatology of at least 30 years. | The manual rainfall source is incomplete for this use: observed local-file timestamps span 2000-2014. Three non-contiguous IMD years are insufficient. The model accepts a user-supplied monthly CSV but does not authenticate it. | At least 30 consecutive quality-controlled monthly rainfall years at one homogeneous station/location, plus source/storage, demand, soil-moisture and independently reviewed drought impacts for consequences/validation. | Descriptive historical precipitation anomaly only if the user supplies eligible data; not a water-shortage estimate or forecast. No qualifying local series is currently integrated. |
| Industrial incident | Pollutant-specific concentration/reference comparison only when units and averaging periods match exactly. Source/dispersion modelling would require a separately verified emissions inventory and meteorology. | KSPCB AQI summaries/reports and industrial consent records provide dated context; the available files do not establish a source-attributed pollutant time series or current release. | Quality-assured pollutant observations and co-located meteorology; current operating/emissions/stack data; terrain; source-apportionment evidence; exposure and independently reviewed outcomes. | Optional like-for-like descriptive ratio only. No source attribution, plume, compliance finding, health impact or affected-area prediction. |
| Infrastructure failure | Qualitative failure-mode/effects and dependency review (FMEA concepts); no occurrence, criticality or risk-priority number without calibrated scales and asset records. | OSM road snapshot is not a verified network/condition layer. NIHFW hospital records are review-only. Conceptual power/water/road/hospital dependencies are explicitly unresolved. | Owner-confirmed asset/network locations, condition, capacities, topology, backup/redundancy, outage/failure/repair history and service-impact records. | Qualitative user-report/dependency review only. No failure probability, route/access estimate, service-loss forecast or asset ranking. |
| Compound: cyclone + flood | Keep cyclone and flood components separate; represent interaction as an unresolved dependency until event times, spatial overlap, boundary conditions and outcomes are compatible. | Context snapshots exist for rainfall, river level, meteorology and a JRC return-period scenario, but they are not a synchronized event dataset. | Time-matched cyclone track/wind/rain, river/coastal water, drainage state, compatible flood footprint/depth, asset exposure and independent outcomes. | Separate component indicators and qualitative pathways only. No summed score, joint probability, interaction multiplier or cascade prediction. |
| Compound: heavy rainfall + drainage failure | Rational Method runoff scenario compared with a capacity only when the user explicitly supplies both; comparison is meaningful only under compatible engineering assumptions. | Rainfall observations/grids are incomplete or not joined to an assessed catchment. No verified local drainage inventory/capacity is available. | Subcatchment boundaries, imperviousness, locally applicable design hyetograph/time of concentration, surveyed network/capacity/condition, tide/outfall state and observed inundation. | Explicit flow/capacity scenario comparison only; not proof of actual drainage failure, inundation, location or damage. |

## The only fitted predictive benchmark currently supported by a real series

`src/rainfall_forecast.py` fits a gradient-boosting regression to historical
manual rainfall measurements, but only when the user explicitly runs the
benchmark in the existing hydrology evidence explorer. It predicts the next
source-recorded rainfall reading for exact one-hour station intervals. It is
not wired into live conditions, the hazard-specific flood calculation, or
operational warning.

The global chronological holdout with a seven-day embargo covers 11,675 test
pairs from 2012-06-22 through 2014-12-31 (15 of 21 source stations); 46,621
exact one-hour pairs were used for training. The source copy contains 109,978
valid rows from 2000-02-27 through 2014-12-31, despite its filename implying
1991-2020 coverage. Test values contain no exact zero-rain observations, source
timezone is undocumented, and event group identifiers are absent. These
results are a retrospective measurement benchmark, not evidence of local
Kochi forecasting skill, flood prediction, causal impact or operational
reliability. See `PHASE_4_VALIDATION_REPORT.md`.

The separate flood classifier in `src/flood_model.py` is fail-closed. Its
five-row example file is not eligible for training or prediction. The
chronological/event-separated evaluation pipeline remains available for future
verified data, but no classifier was fit and no flood probability was
calculated.

## Consequence and spatial model selection

The shared assessment builder in `src/disaster_models/common.py` emits four
distinct consequence categories—human, infrastructure, environmental and
economic. Each category reports unavailable observed impacts, no modelled
estimate, evidence needed, and `INSUFFICIENT EVIDENCE` until compatible data
are available. User-entered population and nominated assets remain context,
not exposure estimates.

Current spatial files do not justify facility/ward exposure calculations:

- The provisional Kochi Corporation boundary passes required provenance
  checks but its polygon self-intersects; it is not used as a coverage mask.
- The processed community ward layer contains 74 polygons that pass the
  repository geometry check. The source review records three invalid polygons
  excluded from the 77-row source and six records missing ward identifiers.
  The layer is not a current/legal boundary, hazard footprint or exposure
  basis.
- NIHFW's 180 Ernakulam hospital rows have 31 missing/nonnumeric coordinate
  pairs and 18 repeated coordinate-pair groups covering 63 rows. Coordinate
  order, CRS/datum and per-record accuracy are undocumented; no hospital
  points are eligible for raster sampling.
- KSDMA raster value semantics and reuse conditions remain unresolved. JRC
  GloFAS RP100 is a model scenario, not an observed flood footprint or
  validated site-impact layer. No population, drainage, utility or
  owner-confirmed critical-facility layer is spatially joined.

Therefore no map in the decision workflow identifies a ward, person, hospital,
road or other asset as exposed or safe. Proximity is not treated as exposure.

## Method references

The existing model modules contain the method-specific reference URLs and
limitations. Key sources include FHWA HEC-22 for urban drainage design; WMO's
SPI User Guide; NOAA/NWS heat-index method documentation; USGS MMI and landslide
process references; WHO air-quality guidance and U.S. EPA AERMOD input
requirements; NIST community resilience planning; IEC 60812 FMEA; and
Zscheischler et al. (2020) for compound-event typology. Reference applicability
to local Kerala operations must be reviewed by competent local authorities.
