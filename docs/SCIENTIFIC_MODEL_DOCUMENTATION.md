# Scientific model documentation

**Review date:** 2026-11-02
This document records what the current application calculates and what it
does not infer. “Scenario indicator” means arithmetic under user-supplied
assumptions, not a forecast or verified local consequence.

## Shared consequence contract

Every hazard assessment contains the four categories `human`,
`infrastructure`, `environmental`, and `economic`. Each category separates:

- observed impact (currently unavailable);
- a modelled estimate (normally not calculated);
- user-supplied context (never treated as exposure);
- location-specific and validation flags; and
- evidence needed to progress.

When compatible evidence is absent, the category is
`INSUFFICIENT EVIDENCE`. No population, damage, service loss, environmental
impact, casualty or financial value is inferred.

One explicitly supported exception is the heavy-rainfall/drainage *scenario
capacity indicator*. When the user supplies rainfall amount and supported
duration, catchment area, runoff coefficient and positive drainage capacity,
the model calculates a Rational Method peak-flow scenario and compares it
with that capacity. The infrastructure category then displays the scenario
flow, capacity, ratio, and non-negative nominal exceedance. This is not a
prediction of actual drainage failure, surcharge, flood extent, asset damage,
or service interruption, and does not change the human, environmental or
economic categories from insufficient evidence.

## Model contracts

| Model | Input-driven calculation | Consequence boundary |
|---|---|---|
| Flood | Mean user-entered rainfall depth/duration; optional `Q = 0.00278 C i A` with area in hectares and mean intensity in mm/h. | Runoff is a scenario flow indicator, not inundation depth/probability. No local threshold, flood footprint or consequence map. |
| Cyclone | Convert supplied wind km/h to m/s and idealized dynamic pressure `q = 0.5 rho v^2`, using fixed `rho = 1.225 kg/m³`. | Not structural load, damage, surge, or a consequence estimate. NOAA IBTrACS historical best-track data are acquired but withheld from the app pending rights clarification; they do not supply a local forecast or consequence estimate. |
| Earthquake | Optional reported MMI is range-checked and described ordinally. | No site shaking or damage conversion. |
| Landslide | Mean rainfall rate over an explicitly supported input period. | No local threshold or terrain-conditioned trigger; no exposure estimate. |
| Heatwave | NOAA/NWS Rothfusz regression and published adjustments in its stated warm/humid applicability domain. | Screening band only; no local health trigger, personal heat stress, or health-outcome estimate. |
| Drought | SPI-1 calendar-month gamma fit with zero adjustment and normal quantile transform, gated on a complete minimum 30-year monthly reference. | Precipitation anomaly only; no supply deficit, agricultural loss, or drought forecast. |
| Industrial incident | Concentration/reference ratio only when numeric values, units and averaging periods match. | No source attribution, dispersion, legal finding, or exposure estimate. |
| Infrastructure failure | Qualitative user report and conceptual dependency/FMEA review. | No failure frequency, reliability, repair time, or service disruption estimate. |
| Cyclone + flood | Run wind and rainfall/runoff components separately; dependency remains unresolved. | No joint probability, summed score, interaction multiplier or combined consequence prediction. |
| Heavy rainfall + drainage failure | Rational Method scenario flow compared with user-entered capacity; output is tied to both rainfall and capacity inputs. | No verified overflow, inundation, exposed people/assets, damage or loss. |

## Evidence and uncertainty semantics

- User inputs are not authenticated. `SIMULATED SCENARIO`, `OBSERVED —
  USER-REPORTED`, and `FORECAST — USER-SUPPLIED` remain distinct in the app.
- All local predictive claims are `NOT YET VALIDATED`.
- An output without matched source data is not a zero-risk or zero-consequence
  finding.
- Geometry proximity is not exposure. No point/ward overlay is enabled for
  unverified hospital coordinates, invalid corporation boundary, or
  semantically unresolved hazard raster.
- Percent confidence, probabilities and prediction intervals are not
  generated because calibration and outcome evidence are inadequate.
- Recommendations identify why relevant, evidence/authority, general versus
  location-specific scope, and limitations; all remain unranked.
- The long-term planning action is generated separately for every hazard and
  requires verified footprints/assets/outcomes before location-specific
  investments; it is not a project selection or benefit estimate.
- The Decision Workflow can transfer a submitted assessment to the existing
  Kochi map. Scenario inputs and model indicators remain labelled as user
  supplied or modelled; they are not converted into map exposure. The JRC
  RP100 layer is shown only as separate flood-scenario context for flood
  selections, not as a result calculated from the selected scenario.
- ESA WorldCover 2021 v200 is shown as a checksum-verified categorical
  context preview for selected hazards, with its source year and class legend.
  The crop is a fixed approximate review rectangle, not a municipal-boundary
  clip. It is not a hazard model, imperviousness estimate, population layer,
  or consequence input.
- Selecting a displayed GeoJSON feature reveals its recorded attributes only.
  The current incomplete ward layer does not establish complete ward coverage,
  hazard severity, population, or facility exposure.
- NOAA NCEI IBTrACS v04r01 has been preserved and structurally validated as a
  North Indian Ocean CSV snapshot, but the source product page and DOI
  metadata inspected did not provide dataset-level reuse terms. It is not
  displayed or used by the app pending NCEI clarification. Its historic
  positions/intensity are not local wind, surge, exposure, or damage evidence.

## Historical rainfall benchmark

The separate optional benchmark in `src/rainfall_forecast.py` uses observed
manual hourly source rows and a chronological split to evaluate next-record
rainfall measurements for exact one-hour station intervals. It compares
persistence, station median and gradient boosting. It does not feed the
disaster assessment and does not validate flood or consequence predictions.
Sample size, scores, leakage limits and source limitations are documented in
`MODEL_VALIDATION_REPORT.md`.

## References and data prerequisites

Method references are attached to the model source modules. These include
FHWA HEC-22, WMO SPI guidance, NOAA/NWS heat-index documentation, USGS MMI and
landslide references, WHO air-quality guidance, EPA AERMOD input requirements,
NIST community resilience planning and compound-event literature. Local
thresholds and decisions require relevant Kerala/Indian authority adoption
and expert review. Dataset-specific sources, licences, coverage and unresolved
quality requirements are in `DATA_SOURCES.md`,
`DATA_QUALITY_REPORT.md`, `DATA_TO_MODEL_MAPPING.md`, and
`DATA_GAPS_AND_REQUIREMENTS.md`.
