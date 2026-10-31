# Evidence and data gap closure register

**Reviewed:** 2026-10-31  
**Purpose:** Turn the existing multi-hazard source inventory into a traceable plan for evidence-backed research. This register does not certify any forecast or assert that all ten models exist.

## Decision rule

Keep the ten scenario choices available in the interface, but distinguish them from independently trained models. For every hazard, record the source, licence, spatial and temporal coverage, target definition, observation time, missingness, group/event identifiers, transformations, checksum and limitations. A source becomes a candidate training table only after labels and predictors are joined without leakage. A model becomes a candidate for promotion only after leakage-safe holdout evaluation against a baseline and a documented review.

## Current repository evidence

The repository's `reports/hazard_dataset_readiness.json` says there are raw source files for seven of nine non-flood source tracks, but no claim of a validated local prediction model follows from that count. Existing acquisition records also document Kerala rainfall telemetry (188,045 rows; 108 stations), river-level telemetry (465,076 rows; 26 stations), and an historical flood inventory (6,876 event rows; 86 rows mention Ernakulam). These are source inventory counts, not verified Kochi flood labels. The hydrology source timestamps/timezone, river-gauge datum/station identity, event alignment, and local boundary relevance remain material limitations.

## Source-to-gap register

| Scenario option | Evidence/data source to pursue | What it can support now | Missing evidence before a predictive claim |
|---|---|---|---|
| Flood | INDOFLOODS (IIT Delhi/HydroSense Lab, Zenodo); IFI-Impacts historical inventory; Kerala Surface Water/NWDP rainfall and river telemetry; KSDMA flood maps | Historical event/gauge audit, source comparison, candidate event-severity research, static hazard context | Verified gauge IDs/datum and timestamps; event-time aligned predictors; defensible non-event periods; local urban flood extent/depth labels; license check; event- and time-separated holdout |
| Cyclone | NOAA/NCEI IBTrACS best-track archive; cross-check against official IMD/RSMC New Delhi best-track material | Historical storm-track and intensity summaries; storm-level research | Audit suspect/duplicate points; verify official source and terms; storm/season holdout; forecast-time predictors; local wind/rain/surge impact labels |
| Earthquake | USGS ComCat for catalogue QA; India-specific National Center for Seismology (NCS) catalogue and GSI seismotectonic/geology evidence for cross-check | Historical event catalogue and hazard-context research | Do not predict occurrence from an event catalogue. For impact research, obtain local ground-motion/shaking observations, site/geology data, exposure/building vulnerability, and observed damage labels |
| Landslide | KSDMA-hosted GSI Ernakulam susceptibility layer; NASA Global Landslide Catalog as a supplementary inventory | Susceptibility/context review and inventory cross-check | GSI provider clarification on three invalid source polygons, legend/scale/licence and boundary alignment; bias-aware background samples; rainfall/time alignment for any temporal model |
| Heatwave | Existing daily weather time series; IMD forecast/warning/rainfall/weather products; authoritative temperature observations where available | Historical temperature and threshold summaries | Define a defensible local heatwave threshold; resolve station/coverage gaps; future-time split; avoid using future observed weather as a predictor; validate against a simple persistence/climatology baseline |
| Drought | Existing drought-index/area time series plus KSDMA drought susceptibility maps and authoritative rainfall observations | Drought history and susceptibility/context summaries | Confirm index definition, units, temporal coverage, spatial resolution and source licence; construct future-period targets; evaluate chronologically and locally |
| Industrial incident | KSDMA major industrial accident hazard zones; Kerala Factories/industrial regulator and official incident reports where openly available | Static hazard-zone context and a source-discovery starting point | Verified incident dates/type/severity, facility identity and location, exposed population/assets, facility process/hazard data and suitable non-incident/background periods. A hazard-zone map is not incident probability |
| Infrastructure failure | Official public-works, road, drainage, utility and municipal asset records; verified failure/repair/closure incident logs where released | Infrastructure inventory and resilience planning if the asset data are licensed and current | Consistent asset IDs and locations, dated failure/outage/closure outcomes, maintenance/exposure variables, coverage of non-failure periods, and a defined target/horizon. Do not infer failures from missing map features |
| Compound cyclone + flood | Join cyclone track/forecast evidence with rainfall, tide/surge, river/flood observations and verified impact/closure/inundation records | Scenario dependency mapping and retrospective case studies | Common timestamps/time zone, coastal/river/drainage interactions, verified joint-event cases and non-joint controls, event-level holdout. Do not multiply separate hazard scores and call it a calibrated joint probability |
| Compound heavy rainfall + drainage failure | IMD/NWDP rainfall; official municipal drainage/capacity/maintenance data; dated waterlogging/inundation/complaint/closure records | Mechanism-based scenario assessment and data-gap mapping | Verified drainage network/capacity and condition, time/location-stamped urban waterlogging labels, rainfall aligned to lead time, reporting-bias controls and independent holdout cases |

## Authoritative source links

- KSDMA hazard-map catalogue: https://sdma.kerala.gov.in/hazard-maps/
- KSDMA State Disaster Management Plan and Orange Book: https://sdma.kerala.gov.in/sdmp/
- INDOFLOODS dataset (Zenodo record 14584655): https://zenodo.org/records/14584655
- IFI-Impacts dataset (1967–2023): https://zenodo.org/records/16994648
- HydroSense Lab published research datasets and citation details: https://hydrosense.iitd.ac.in/resources/
- NOAA/NCEI IBTrACS: https://www.ncei.noaa.gov/products/international-best-track-archive
- USGS ComCat event service: https://earthquake.usgs.gov/fdsnws/event/1/
- IMD public API reference (forecasts, warnings and rainfall endpoints): https://api.imd.gov.in/public/api_reference.html
- Kerala State Pollution Control Board air-quality portal: https://kspcb.kerala.gov.in/aqi
- CPCB National AQI portal: https://airquality.cpcb.gov.in/AQI_India/

The links above are source discovery and evidence references, not a statement that each source's full dataset has been downloaded, is openly redistributable, or is suitable for every proposed target. Confirm current licence/terms at source before reuse or redistribution.

## Immediate work order

1. **Flood first:** execute the existing manual `Acquire INDOFLOODS and train flood research baseline` workflow; preserve the artifact and inspect the audit and metrics. The script's documented target is danger-level exceedance among already-recorded flood events, not flood occurrence. Review whether event-scale precipitation windows could leak the target before treating the metrics as evidence of predictive skill.
2. **Reconcile existing raw sources:** run `python scripts/audit_hazard_datasets.py` and preserve its readiness report; then inspect each present source for row counts, date coverage, missingness, duplicates, licence, label availability, and Kochi/Ernakulam relevance.
3. **Close source-specific blockers:** request clarification for invalid GSI geometry and unresolved hydrology gauge datum/identity; verify official cyclone-track records and licensing; cross-check the earthquake catalogue with NCS/GSI evidence.
4. **Acquire the missing incident/outcome evidence:** industrial incident logs, infrastructure failure/repair logs, urban waterlogging/drainage records, and suitable heat/drought/air-quality time series with documented source terms.
5. **Build separate targets:** never merge distinct hazards into one label. Each target needs a stated spatial unit, prediction horizon, event definition, positive/negative sampling method and source-specific provenance.
6. **Promote only on evidence:** use grouped and chronological holdouts as appropriate, compare to a naive baseline, report sample/event counts and uncertainty, and keep local prediction claims disabled if the data are insufficient.

## Promotion checklist

- [ ] Source publisher and exact file/version recorded
- [ ] Current licence/terms reviewed
- [ ] Retrieval timestamp, checksum, units, CRS, spatial and temporal coverage recorded
- [ ] Label definition and forecast horizon fixed before fitting
- [ ] Missingness, duplicates, coordinate/time validation and event IDs audited
- [ ] Negative/background periods independently justified
- [ ] No target leakage or post-event features
- [ ] Group/time/geographic holdout chosen to match intended use
- [ ] Baseline comparison and suitable metrics reported with sample counts
- [ ] Kochi/Ernakulam transfer limits explicitly assessed
- [ ] Independent review completed before any “validated prediction” label

**Current conclusion:** the evidence supports source auditing, historical summaries, susceptibility context and selected research-baseline experiments. It does not yet justify ten calibrated disaster forecasts for Kochi.