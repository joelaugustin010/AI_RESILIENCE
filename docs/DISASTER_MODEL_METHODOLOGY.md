# Hazard-specific model methodology

**Status:** Implemented screening and scenario calculations; no model is
historically validated or enabled as a prediction system. Exact workflow
labels remain defined by `src/decision_workflow.py`.

| Existing workflow option | Model and scientific method | Data used for calculations | Main output and boundary |
|---|---|---|---|
| Flood | Rainfall depth/duration descriptor; optional Rational Method peak runoff, `Q = 0.00278 C i A` for `i` mm/h and area `A` hectares. | Only user-entered rainfall depth/duration, catchment area and runoff coefficient. NWDP/IMD/JRC assets are context-only and not joined. | Mean rainfall rate and optional simplified peak-flow estimate. No inundation, flood severity, return period or exposure is inferred. |
| Cyclone | Convert entered wind speed and compute idealized dynamic pressure `q = 0.5 rho v^2` with stated air-density assumption. | Only user-entered wind speed. NASA POWER is fixed-point daily context; it is not event wind. No acquired storm track is used. | Wind/pressure physical indicators only; no cyclone category, track, surge, building load or damage estimate. |
| Earthquake | Optional reported Modified Mercalli Intensity (MMI) descriptive scale review based on USGS qualitative descriptions. | Only optional user-reported MMI. The USGS query snapshot returned no events and is not used to infer hazard. | Reported ordinal intensity descriptor; no ground motion, site amplification, damage or vulnerability calculation. |
| Landslide | Rainfall intensity-duration context. Published rainfall-trigger thresholds are empirical and region-dependent; none is applied without local calibration. | Only user-entered rainfall depth/duration and optional antecedent total. IMD/NWDP files are not location/time matched to the slope. | Mean rainfall rate and explicit threshold unavailability; no susceptibility or trigger classification. |
| Heatwave | NOAA/NWS Rothfusz heat-index regression with published humidity adjustments and stated domain. | User-entered temperature and relative humidity only. NASA POWER does not supply a verified co-located event humidity input. | Calculated screening heat index when valid; U.S. bands are labeled and not treated as Kerala warnings, medical triage or forecast. |
| Drought | SPI-1: calendar-month gamma distribution fit, zero-probability adjustment, normal quantile transform, and standard SPI category bands. | User-supplied single-station monthly precipitation CSV only; requires at least 30 complete consecutive years. Existing rainfall files/grids are not silently promoted to a complete reference series. | Descriptive standardized precipitation anomaly for the last month; not soil-moisture drought, impact or forecast. |
| Industrial incident | Pollutant-specific concentration/reference ratio only when units and averaging periods exactly match. This is not dispersion modelling. | User-supplied measurement and comparator only. KSPCB AQI and permit documents do not provide source attribution. | Matched comparison ratio only; no confirmed incident, compliance result, plume, exposure or causal source claim. |
| Infrastructure failure | Qualitative failure-mode/effects and dependency-pathway review; no occurrence/severity/detectability score is assigned. | User-described failure/service and nominated assets. OSM roads and unverified hospital/boundary data are not joined. | Review pathways and operator evidence needs; no reliability, outage probability, service-loss or recovery-time estimate. |
| Compound: cyclone + flood | Separate cyclone and flood component models plus explicit compound-interaction evidence requirements. | Only user-entered component observations/scenario inputs. No matched event-time/cyclone/rainfall/river/coastal/flood outcome dataset is available. | Separate component indicators; interaction remains unresolved. No addition, joint probability or interaction multiplier. |
| Compound: heavy rainfall + drainage failure | Rational Method peak-runoff estimate and conditional comparison with a user-entered drainage design capacity. | User-entered depth/duration, catchment area, runoff coefficient and optional capacity. No project drainage network is joined. | Scenario flow and flow/capacity relationship only. Exceeding stated capacity is not proof of actual flooding or drainage failure. |

## Assessment classes

- **Observational assessment:** for values classified by the user as
  observations; the app marks them as unverified. It does not authenticate
  sources.
- **Scenario assessment:** for hypothetical assumptions or user-provided
  forecast context; not a prediction.
- **Validated prediction:** unavailable for all ten models. There is no
  calibrated forecast model with independent, leakage-safe local validation.

## Shared output contract

Every model returns the exact selected disaster, model ID, assessment type,
result status, inputs, hazard assessment, methodology/calculation, population
and infrastructure evidence status, consequence pathways, before/during/after
recommendations, data-source relevance, uncertainty, data gaps, assumptions,
and validation status. User-nominated assets and population counts are not
recast as model-estimated or spatially verified exposure.

## Scientific references

See `SCIENTIFIC_REFERENCES.md` for source details, publication citations and
the role/limits of each method. Software tests establish implementation
behavior, not scientific validity.
