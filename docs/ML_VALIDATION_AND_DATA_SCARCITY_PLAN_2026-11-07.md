# ML validation and data-scarcity operating plan — 2026-11-07

## Scope and decision rule

This plan applies to the ten-hazard AI_RESILIENCE workflow and its Kochi/Ernakulam coastal-monsoon focus. It separates four concepts:

1. **Trained artifact** — an algorithm fitted to a documented dataset.
2. **Research signal** — a score that may help explore patterns but has not passed independent validation.
3. **Validated predictor** — a model that beats a relevant baseline on independent temporal and spatial data, with acceptable calibration/uncertainty and a defined domain.
4. **Operational warning component** — a validated predictor additionally supplied with current authoritative inputs, monitored prospectively, reviewed by responsible domain authorities, and governed by a deployment protocol.

No amount of synthetic data, imputation, model complexity, or transfer learning can substitute for independent observed outcomes. The strict helper in `src/ml/validation_gates.py` deliberately leaves the current cards in `RESEARCH_ONLY`. The observed-panel contract in `src/ml/local_panel_contracts.py` prevents unobserved intervals from silently becoming negative labels.

## Phase 1 — Model risk and signal audit

The persisted registry currently contains nine model artifacts: six classification tasks and three regression tasks. Model cards report a single temporal holdout and explicitly say they are not independently validated. The current registry reports ten workflow hazards, seven with some trained model evidence, four with hazard-specific usable research models, three with no trained model evidence, and zero independently validated operational models.

| Hazard/task | Current evidence | Main risk / boundary |
|---|---|---|
| Extreme rainfall (Kochi reanalysis point) | Weak research signal | Ranking is better than prevalence, but Brier score is worse than base-rate reference; not a calibrated probability. Rainfall is not flood occurrence or inundation. |
| Next-day precipitation regression | Weak research signal | One temporal holdout; no calibrated interval; grid point is not a station or ward forecast. |
| High temperature classification | Research signal, not validated | Strong one-holdout ranking but visible calibration gaps; not a heat-health impact forecast. |
| Next-day maximum-temperature regression | Weak research signal | Small improvement over persistence on one temporal holdout; no independent spatial or prospective validation. |
| Drought onset | Re-trained research artifact | Must use future-only onset labels and dry-spell definitions; do not reuse backward-looking or invalidated target scores. |
| Cyclone rapid intensification | Weak research signal | IBTrACS best-track is retrospective; rare events and basin transfer risk; not a real-time track/landfall forecast. |
| Cyclone wind change regression | Weak research signal | Storm-grouped holdout is useful, but one temporal holdout and retrospective best-track inputs do not make it operational. |
| Earthquake aftershock | Weak research signal | Screens only after an observed mainshock; catalogue completeness, sequence dependence and regional transfer matter. It does not predict mainshocks or shaking. |
| Cyclone + rainfall | Exploratory concurrent association | No forecast lead time; poor Brier skill versus base rate; concurrent association is not causality or joint impact probability. |
| Landslide | No defensible supervised model | Presence-only inventories do not provide verified non-event samples; reporting bias and spatial sampling bias are severe. |
| Industrial incident | No defensible supervised model | No facility × time panel with incident and non-incident operating periods, exposure/process covariates and verified outcomes. |
| Infrastructure failure | No defensible supervised model | No asset-level failure, outage, restoration and exposure history panel. |
| Heavy rainfall + drainage failure | Component evidence only | No ward/drain-level observed overflow or inundation outcome panel to train the compound target. |

The hazard registry has ten entries because the two compound scenarios are part of the authoritative workflow; the table above also separates their underlying component tasks to make the evidence boundary explicit.\n\nThe new `src/ml/local_panel_contracts.py` helper audits proposed observed-outcome panels. It rejects missing provenance, invalid intervals, duplicate unit/time rows, unknown negatives and synthetic/simulated rows as training evidence. Its configured row-count floor is a screening threshold, not proof of statistical adequacy.

### Release-blocking risks

- A single chronological holdout is not independent validation.
- Calibration curves and ECE calculated on the same holdout are diagnostic, not a calibration guarantee.
- A model can rank cases while its probabilities are wrong. Do not show such scores as event probabilities.
- Random row splits are inappropriate for weather sequences, storm tracks, aftershock sequences, repeated sites and nearby wards.
- Reanalysis and global best-track data do not equal local gauge, station, building, drain or facility observations.
- Missing inputs must not be silently replaced by zero, medians, unrelated fields or synthetic labels.
- Hazard forcing (rainfall, wind, temperature) must not be relabelled as hazard impact (flood depth, damage, casualties).

## Phase 2 — Validation and calibration frameworks

### 2.1 Evaluation design

Use nested chronological and spatial evaluation, not random row splitting:

1. **Training period:** fit preprocessing, imputation, feature selection and model parameters only on the training period.
2. **Validation period:** select model family and operating threshold. No final-test tuning.
3. **Temporal final holdout:** reserve later years or complete later storm/event groups.
4. **Spatial holdout:** reserve entire wards, catchments, facilities, asset groups or geographic blocks.
5. **Prospective shadow period:** run with timestamped inputs without issuing warnings; compare later with verified outcomes.
6. **External replication:** where transfer is claimed, test a separate region or sensor network with no target leakage.

For cyclone tracks, group by storm identifier and purge all training rows whose future outcome windows overlap the validation/test boundary. For aftershocks, group by sequence and embargo the full future-label window. For flood and landslide, block by catchment/ward and event, not by raster pixel. For facility and infrastructure panels, group by facility/asset and use time-aware splits.

### 2.2 Baselines and scorecards

Every candidate must be compared against:
- climatology/base-rate probability for rare events;
- persistence and seasonal-naive baselines for weather;
- a simple physically meaningful baseline where available;
- a no-change baseline for continuous forecasts.

Binary tasks: report event count, prevalence, precision, recall, F1, PR-AUC, ROC-AUC, Brier score, log loss, reliability curve, ECE, confusion matrix at a validation-selected threshold, and uncertainty intervals. For rare events, PR-AUC and event counts matter more than accuracy.

Regression tasks: report MAE, RMSE, bias, R², baseline skill, error by season/region/intensity band, and interval coverage/width. Report performance by event group, not only pooled rows.

### 2.3 Calibration and uncertainty

`src/ml/validation_gates.py` adds:
- `binary_calibration_report`: Brier score, base-rate Brier reference, Brier skill and reliability-bin/ECE diagnostics.
- `split_conformal_interval`: finite-sample split-conformal residual intervals for regression, with explicit exchangeability warning.
- `model_card_validation_gate`: a fail-closed operational gate requiring independent temporal and spatial passes, calibration, baseline skill, complete provenance, domain-transfer evidence and at least 100 independently held-out positive events.
- `registry_validation_summary`: a registry-wide readiness summary.

For time-series and spatially dependent data, ordinary iid conformal assumptions do not hold automatically. Use block/cluster conformal calibration and verify empirical coverage on separate future blocks or held-out storm/site groups. Keep calibration data separate from model fitting and final evaluation. Never calibrate on the final test set and then report that same set as untouched.

For rare-event probability calibration, compare Platt/logistic and isotonic calibration only within training/validation folds. Isotonic needs enough events; if sample size is insufficient, keep scores uncalibrated and research-only. Thresholds should be chosen on validation data using a documented decision-cost or recall/precision target, never tuned on final test outcomes.

### 2.4 Minimum promotion criteria

A model may be considered for domain review only after all are true:
- target definition and input timestamp are operationally available;
- leakage audit passes and preprocessing is fitted within folds;
- at least two temporal holdouts and one independent spatial holdout pass;
- baseline skill is positive with uncertainty bounds that do not indicate material harm;
- calibration is acceptable against a base-rate reference and stable across seasons/regions;
- sample/event counts are sufficient and subgroup failures are disclosed;
- missingness, out-of-domain and drift monitoring are implemented;
- provenance and reproducibility are complete;
- prospective shadow evaluation confirms the offline results.

The helper's 100-event floor is a conservative minimum gate, not a universal statistical guarantee. More data may be required for rare hazards, subgroup claims or high-consequence use. Passing software checks alone cannot set a model card to operational.

## Phase 3 — Data scarcity and synthesis strategy

### 3.1 Flood and drainage failure — highest local priority

Build a site/event panel at ward, catchment, drain segment or monitored location level. Candidate features:
- time-aligned IMD/NWDP/CWC rainfall, local gauges and tide/estuary level;
- drain/canal geometry, invert levels, capacity, outfall constraints, blockage/maintenance records;
- Sentinel-1 flood extent and verified water-level/depth observations;
- elevation, slope, land cover, imperviousness and soil/infiltration proxies;
- asset/road/building exposure and population grids;
- event-specific observed inundation, depth, duration, closure and damage outcomes.

Use NRSC/ISRO flood atlas, Global Flood Database and DFO as event discovery/context sources, not automatically as ward-level labels. The India Flood Inventory audit found 6,876 records but no complete coordinate pairs for the Kerala/Ernakulam text matches; it is not ready to train local flood footprints. Acquire georeferenced footprints, verify dates and spatial precision, then join to time-aligned rain/tide/drainage observations.

### 3.2 Landslide

Use NRSC Landslide Atlas and KSREC/SILAAS inventories as presence/event sources. Add verified non-event observation windows only where a survey or monitoring system confirms that the slope was observed and no event occurred. Do not treat every unlisted pixel as a safe negative. Build slope-site × monsoon-window panels with rainfall antecedents, geology, soil, land cover, drainage, road cuts and verified event dates. Use spatial blocks by slope/catchment and account for inventory reporting bias.

Until then, deliver susceptibility context and rainfall-trigger screening as separate evidence layers; do not call them a supervised probability of landslide occurrence.

### 3.3 Industrial incident

Create a facility × operating-period panel from authorized DGFASLI/state factory safety records, KSPCB consent/inspection/monitoring records, incident reports and facility/process registries. Required fields include facility identity and coordinates, process category, operating status, hazardous inventory, inspection/maintenance state, verified incident/near-miss outcomes, incident date and source confidence. Non-incident periods must be confirmed operating periods, not simply missing incident reports. Protect confidential facility and worker data.

Use Edayar industrial estate records for exposure and facility inventory, not as incident labels. Do not train on public news counts alone.

### 3.4 Infrastructure failure

Obtain KSEB feeder/DTR outage and restoration histories, water/sewer pump and treatment plant outage logs, road closure/bridge inspection records, asset age/capacity and maintenance logs. Build asset × time intervals with verified failure onset, outage duration, restoration, weather exposure and service population. Aggregate public KPIs are context only; they cannot substitute for asset-level outcomes.

### 3.5 Transfer learning and domain adaptation

- Start with proxy-region datasets only when target definitions, sensor units, sampling cadence and causal mechanisms match.
- Use leave-one-region-out tests before transferring to Kochi. Hold out entire source regions and evaluate the target region separately.
- Prefer hierarchical or region-conditioned models with explicit region effects; compare source-only, target-only and pooled models.
- Fine-tune only on a documented local calibration sample; report performance before and after adaptation.
- Reweight source samples only with a justified covariate-shift assumption and overlap diagnostics. If Kochi lies outside source support, abstain.
- Never transfer cyclone basin best-track models directly into a local wind-impact predictor; never transfer US outage labels into Kerala infrastructure-failure labels.

### 3.6 Synthetic and physics-informed augmentation

Permitted uses:
- test parser, feature-engineering and inference behaviour;
- stress-test plausible rainfall/tide/drainage combinations;
- generate simulator-trained emulators when simulator inputs and outputs are aligned and the emulator is explicitly labelled simulation-trained;
- explore sensitivity and failure modes under bounded physical assumptions.

Not permitted:
- synthetic points counted as observed events or non-events;
- simulated flood extents mixed into observed labels without provenance and a separate domain indicator;
- synthetic data used in the final independent validation set;
- interpolated risk maps represented as measured local hazard observations.

Every synthetic record must include `record_origin=synthetic_or_simulated`, generator/version, physical constraints, parameter range, seed and provenance. Keep it in a separate partition. Test the emulator against independent observed data before using it for real-world claims.

### 3.7 Missing data and spatial interpolation

- Fit imputers on training folds only; add missingness indicators and report feature-level missingness.
- Do not impute target labels. Do not fill missing incident records with negatives.
- For weather inputs, use source hierarchy and time alignment (station/gauge first, then quality-controlled gridded data) with source uncertainty retained.
- Spatial interpolation (e.g. kriging/IDW) may estimate a continuous environmental covariate only after variogram/coverage diagnostics and spatial cross-validation. It must not create pseudo-observed flood depths, failures or incident labels.
- Publish coverage masks and uncertainty surfaces. Withhold ward-level values where sensor coverage is inadequate.

## Phase 4 — Integrated resilient pipeline architecture

Recommended flow:

`source registry → immutable raw data + checksums → schema/time/CRS validation → event/site panel builder → leakage-aware temporal + spatial split → fold-local preprocessing → baseline and candidate training → calibration/uncertainty → independent validation gates → model card + registry → fail-closed inference service → monitoring + human review`

### Runtime rules

- Keep the deterministic evidence-based decision workflow as the authoritative assessment path.
- ML is supplementary until a card passes independent validation and domain review.
- If required features are missing, timestamps are stale, data provenance is incomplete, or inputs are outside training support, abstain rather than extrapolate.
- Display task, target, location, issue time, evidence tier, validation status, uncertainty, baseline comparison and limitations beside every model output.
- Never convert a rainfall forecast into a flood warning, a cyclone best-track estimate into a landfall forecast, or a hazard score into expected casualties.
- Keep all ten hazards selectable. For hazards without models, show the missing evidence and robust preparedness actions.
- Store prediction inputs, model hash, output, timestamp, source versions and later verified outcomes for prospective evaluation.
- Monitor feature drift, missingness, calibration drift, alert burden and subgroup performance. Disable a model automatically if required sources go stale or a safety gate fails.

### Local evidence acquisition queue

| Priority | Dataset / owner | Needed structure | Current blocker |
|---|---|---|---|
| P0 | Kochi Corporation / Irrigation Department drainage works | drain segment, geometry, capacity, maintenance, completion date | published work summaries are not an event-aligned asset panel |
| P0 | KSDMA / local bodies / CWC / IMD | verified flood event, ward/catchment, depth/duration, rainfall/tide | event footprints and timestamps need harmonisation |
| P1 | KSREC / NRSC / district disaster management | slope-site event and surveyed non-event windows | presence-only inventory / reporting bias |
| P1 | KSEB / KWA / local asset operators | asset-time outage, failure, restoration and maintenance | aggregate reliability figures are insufficient |
| P1 | DGFASLI / KSPCB / Directorate of Factories | facility operating-time, incident, inspection and exposure | facility-level incident/non-incident access and permissions |
| P2 | Copernicus Sentinel-1 / DEM / land-cover sources | dated geospatial covariates and coverage metadata | processing and ground-truth validation required |

### Completion definition

The system is competition-ready as a **resilience decision-support demonstrator** only when the app is reliable, the local evidence layers are traceable, the demo clearly distinguishes research signals from verified facts, and preparedness recommendations are actionable. It must not be described as an operational disaster-warning system until at least one hazard-specific model passes the full independent validation and prospective governance process.
