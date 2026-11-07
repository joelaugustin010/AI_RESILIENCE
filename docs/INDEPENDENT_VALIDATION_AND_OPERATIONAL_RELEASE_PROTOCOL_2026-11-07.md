# Independent Validation and Operational Release Protocol — 2026-11-07

## Executive decision

The current system is **code-complete research decision support**, not an operational disaster prediction or public warning system. The current model registry reports zero independently validated models. The nine persisted model binaries are research artifacts; their existence, a green software test suite, or a live HTTP health response cannot establish predictive validity.

This protocol defines the evidence required to change that decision. It deliberately does not manufacture holdout scores or claim that an external dataset has been acquired when it has not.

## Phase 1 — Independent validation and holdout verification

### 1.1 Freeze the evaluation contract before opening the holdout

For every model, version and prediction target, create a signed/immutable evaluation manifest containing:

- model ID, artifact SHA-256, code commit, feature schema and training-data provenance;
- target event definition, spatial unit, prediction issue time, lead time and outcome window;
- inclusion/exclusion rules and label adjudication protocol;
- training, calibration, validation and final test periods;
- geographic grouping unit and event grouping key;
- baseline definitions and primary metrics;
- minimum independent groups/events, missingness limits and confidence-interval method;
- external source identity, license, acquisition timestamp and processing version.

Do not tune a threshold, feature, calibration map, imputation method or geographic boundary after examining final holdout outcomes. If the holdout informs any decision, it becomes development data and a new untouched test set is required.

### 1.2 Holdout axes

Use separate, non-substitutable holdouts:

1. **Temporal:** strictly later dates than model fitting; purge labels whose outcome windows overlap split boundaries.
2. **Spatial:** entire districts/catchments/stations/assets withheld, not random rows. For Kochi, retain a separately evaluated municipal/catchment block where labels support it.
3. **Event:** whole cyclone, flood episode, earthquake sequence or industrial incident grouped into one partition.
4. **External-source:** labels and measurements independently maintained from the model's training source/pipeline.
5. **Prospective shadow:** timestamped predictions written before outcomes are known; later join them to adjudicated observations.

A single temporal split, proxy district or random split is not sufficient. Report each axis separately and then a pre-specified joint stress test.

### 1.3 Hazard-specific external evidence

| Target | Independent reference evidence | Required unit of analysis | Known limitation |
|---|---|---|---|
| Rainfall | Independent gauge stations and CWC/state records not used in training | Station × valid time, with station holdouts | Reanalysis grid is not a gauge |
| Flood extent | Independently processed Sentinel-1 SAR event extent and verified local footprints | Event × catchment/pixel with acquisition-time alignment | SAR classification uncertainty, revisit time and water/urban confusion |
| River/drainage | Gauge levels, tide, drain levels/capacity and surveyed obstruction/overflow logs | Gauge/catchment × time/event | Rainfall alone is not inundation |
| Cyclone | Independent best-track source/version and whole-storm holdout | Storm, not individual fix | Best-track is retrospective, not an operational forecast |
| Landslide | NRSC/KSREC verified inventory plus surveyed monitored non-event periods | Slope/site × observation interval | Presence-only events cannot supply true negatives |
| Industrial | Authorised facility incident, inspection, near-miss and operating-period records | Facility × operating period | Missing incident report is not a non-event |
| Infrastructure | Asset-level fault, outage, restoration and maintenance logs | Asset × interval/event | Aggregate feeder KPIs cannot label individual assets |
| Heat/drought | Independent station observations and documented impact/soil-moisture indicators | Station/area × time window | Temperature or rainfall proxy alone is not impact |

For satellite flood comparison, preserve scene ID, orbit/pass, acquisition timestamp, processing algorithm/version, mask quality, georegistration error and reference-label provenance. Score only matched event/time windows. Never call an optical or SAR water mask "ground truth" without its own uncertainty statement.

### 1.4 Metrics and uncertainty

- Classification: event-level precision/recall, PR-AUC, false alarms per site-time, missed-event rate, Brier score, calibration intercept/slope and reliability curves.
- Regression: MAE/RMSE, baseline-relative skill, error by geographic group and prediction-interval coverage/width.
- Spatial: event intersection-over-union, precision/recall of affected area, missed area and false-alarm area; report resolution and geolocation uncertainty.
- Calibration: fit only on a separate calibration partition; assess on a later/spatially independent calibration test. Never calibrate on final test outcomes.
- Confidence intervals: bootstrap independent storms/events/sites/catchments, not individual autocorrelated rows. With too few groups, report descriptive results and "insufficient independent groups"; do not report narrow row-bootstrap intervals.
- Generalisation: publish pooled, per-group, worst-group and leave-one-region-out results. Show the full distribution across held-out groups.
- Baselines: persistence, climatology/base rate, official forecast/product where legally and technically comparable, and simple physical screening baselines.

### 1.5 Pre-registered acceptance floors

There is no scientifically valid universal numerical cutoff across all hazards. Each model's independent evaluation manifest must pre-register hazard-specific floors using decision costs and the intended lead time. At minimum it must require:

- at least three independent geographic groups and at least 30 independent positive events for an initial *candidate review*; more are expected for rare-event operational use;
- positive baseline-relative skill with a confidence interval that does not support material degradation;
- calibration that meets a pre-registered tolerance on independent data;
- no critical worst-group failure or severe subgroup underperformance;
- acceptable false-alarm burden and missed-event rate under the actual warning action;
- complete label, feature, model and source provenance;
- successful prospective shadow evaluation.

These are screening floors, not automatic proof of readiness. If counts are below them, the result is **INSUFFICIENT_INDEPENDENT_EVIDENCE**, not a pass. Official warning issuance additionally requires the responsible authority's approval and procedure.

## Phase 2 — Operational thresholds and warning calibration

### 2.1 State machine

| State | Entry condition | Output |
|---|---|---|
| UNAVAILABLE | Missing/stale/contradictory critical inputs, failed integrity or unavailable model | No numerical score; show reason and safe preparedness guidance |
| RESEARCH_ONLY | No independent spatial + temporal validation | Clearly labelled research result only |
| WATCH | Input contracts pass and an independently reviewed screening signal is available, but warning-grade validation is incomplete | Monitor and prepare; no official warning |
| ADVISORY_CANDIDATE | Hazard-specific independent validation, calibration, uncertainty, baseline and shadow criteria pass | Draft advisory for authorised human review |
| OFFICIAL_WARNING | All technical criteria plus competent authority approval and jurisdictional protocol | Only the authorised agency issues the warning |

The application itself must not represent its output as a government warning. It must show the issuing authority, source, timestamp, expiry and geographic coverage when displaying an externally issued warning.

### 2.2 Threshold selection

For each hazard, define a decision table from observed false-negative and false-positive costs, lead time, action reversibility, population exposure and warning capacity. Select thresholds on development/calibration data only; lock them before final testing. Report sensitivity, specificity, precision, recall, false alarms per location-time, missed events, lead-time distribution and expected action burden. Re-evaluate thresholds when climate regime, sensors, geography, model or intervention policy changes.

Do not copy a probability threshold from one hazard to another. Probability thresholds are not meaningful if probabilities are not calibrated for the intended target and population.

### 2.3 Confidence masking and fallback

- Missing required feature, stale observation, invalid coordinate, failed checksum or artifact mismatch: abstain.
- Outside validated spatial/feature range: mark out-of-domain and abstain from numerical prediction.
- High or unquantified uncertainty: mask probability; display only the reason and evidence.
- Source disagreement: show both sources, timestamps and discrepancy; require review.
- Model unavailable: preserve deterministic evidence-based assessment and preparedness actions.
- No evidence for non-event intervals: do not train or report specificity from those intervals.
- No operational ML status in model card: block official warning state regardless of score.

## Phase 3 — CI/CD and automated deployment verification

### 3.1 Software gates

The repository CI should verify:

- clean Python 3.11 dependency resolution and import/compile checks;
- complete unit/integration suite;
- model-card/registry/artifact consistency;
- all ten hazard registry entries and explicit predictive coverage gaps;
- model artifact checksums and deterministic load/inference smoke tests;
- no model card claims independent validation without its evidence manifest;
- no test or training job silently changes model cards to VALIDATED;
- provenance hash checks on Linux and Windows where applicable.

### 3.2 Live deployment gate

After a main-branch release, check the deployed Streamlit health endpoint and root application shell with retries. Store a timestamped JSON result as a CI artifact. A passing HTTP health test proves availability only; it does not prove model inference, correct data, freshness or predictive validity.

For full release verification, additionally execute an authenticated/non-sensitive in-app smoke test in a controlled environment: load all model cards, load each artifact, run a known non-operational test vector, assert scope and missing-input abstention, and verify that the displayed validation state remains research-only. Do not expose secrets or real user data in CI logs.

### 3.3 Monitoring

Monitor and alert on:

- source freshness and missingness;
- schema/units/range violations;
- feature distribution shift and out-of-domain rate;
- prediction distribution shift;
- calibration and baseline skill after outcome labels mature;
- false alarms, missed events and subgroup/worst-region performance;
- app health, model load failures and latency.

Drift is a trigger for investigation or abstention, not proof that the model is wrong or right. Do not auto-retrain or auto-promote on drift. Freeze the last approved model and roll back on integrity failure.

## Phase 4 — Competition and peer-review audit

### What can be claimed now

- The software repository contains a ten-hazard decision workflow.
- Nine supervised research artifacts and their cards are persisted.
- The current validation report states zero independently validated operational models.
- The application retains deterministic evidence assessment and research-only ML safeguards.
- CI can establish code/test integrity; it cannot substitute for external field validation.

### What cannot be claimed now

- Autonomous or official disaster warnings.
- Flood inundation prediction from rainfall regression alone.
- Kochi-wide spatial generalisation from a single reanalysis grid point.
- Validated landslide, industrial-incident or infrastructure-failure classifiers.
- Operational effectiveness of mitigation interventions without outcome evaluation.
- Real-time satellite observation if the imagery is historical or not freshly acquired.

### Peer-review evidence package

For every candidate model, publish the frozen manifest, source and license register, data-quality audit, geographic/event split map, model card, baseline comparison, calibration plot, confidence interval method, subgroup table, error catalogue, shadow predictions, adjudication record and rollback procedure. Remove sensitive facility/person records or publish only appropriately aggregated results.

### Release decision

**Current release class: RESEARCH / DEMONSTRATION ONLY.** Software CI passing and a live app responding are necessary engineering checks, not evidence of predictive operational readiness. The release must remain research-only until independently sourced ground truth, spatial holdouts and prospective shadow evidence are actually acquired and pass the pre-registered hazard-specific criteria.
