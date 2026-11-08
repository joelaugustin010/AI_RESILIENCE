# AI_RESILIENCE competition readiness report — 2026-11-07

## Executive decision

**Not yet competition-ready as a predictive early-warning system.** The project is a substantial multi-hazard decision-support prototype with nine persisted research model artifacts, a ten-hazard scenario workflow, evidence/provenance controls, and new independent-validation and shadow-monitoring tools. It does not yet have an independently validated operational prediction model for Kochi flood or landslide impacts.

The correct competition claim is: *an evidence-gated multi-hazard resilience prototype that combines research weather models, scenario screening, source-quality audits, and actionable preparedness guidance*. Do not claim a live disaster prediction system, street-level flood forecast, verified lives saved, or operational warnings.

## Model and validation status

- Nine model artifacts are persisted in the repository and registered with model cards.
- The model registry reports zero independently validated models.
- Existing model evaluations are single temporal holdouts. Several classifiers are weak, poorly calibrated, or have invalidated targets/splits and must remain blocked or research-only.
- The Kerala cross-location rainfall experiment (PR #101) tests Kottayam, Wayanad and Thiruvananthapuram training against a spatially and temporally held-out Kochi reanalysis grid point. It has not completed training; no new metric is available.
- PR #101 now compares against both same-day persistence and a training-only calendar-month climatology, reports regression reliability bins and paired seven-day block-bootstrap intervals, and records a promotion gate requiring improvement against both baselines. Even a passing result would not be station-observation validation or a flood forecast.

## Empirical evidence readiness

### Flood

The repository has historical/context sources and an exploratory INDOFLOODS event-severity analysis, but not a training-ready Kochi site × event × time panel. The prior INDOFLOODS experiment used 4,451 event rows from 153 open gauges; test accuracy was below the majority baseline and the task was severity among recorded flood events, not flood occurrence or inundation prediction.

A credible Kochi panel needs time-aligned, licensed and adjudicated:
- rain-gauge observations with station identity, UTC timestamp, accumulation interval and units;
- river-level observations with gauge identity and vertical datum;
- tide observations with station identity and vertical datum;
- Sentinel-1 SAR scene/acquisition/processing metadata and reviewed inundation masks;
- field or official flood observations, depth/duration where available, and verified site/catchment identity;
- monitored non-event periods with known observation coverage.

The panel audit added in PR #99 checks schema, provenance, temporal alignment, duplicates, and reviewed labels. It deliberately always returns `training_ready=false`; schema validity is not ground-truth validation.

### Landslides

The available catalogues are event-presence inventories, not representative non-event panels. A non-event is valid only for a monitored slope-unit period with documented coverage and inspection. Unmonitored sites remain unknown. The audit now rejects unreviewed labels and unsupported non-events. Terrain, rainfall, soil moisture and movement/instrument records must be time-aligned and spatially blocked before supervised training.

### Industrial and infrastructure hazards

Facility-level incident/non-incident histories and asset-level fault/restoration histories remain unavailable. Aggregated state statistics, missing public reports, feeder-level KPIs and community-mapped facility points cannot be converted into facility/asset negative labels.

## CI/CD and runtime

The Actions runs inspected include 866, 868, 876, 878, 880, 882 and 884. Windows and Ubuntu jobs repeatedly fail with no step records, no log URL and no downloadable job log. The independent PR #101 training job has the same failure signature. Rerun requests were accepted but did not create step logs.

The evidence does not identify a code-level Python/YAML/dependency failure. It is consistent with a GitHub Actions workflow admission or runner-provisioning problem, but the definitive internal cause requires GitHub Support. Billing usage reviewed earlier does not prove the Actions budget was exhausted.

PR #99 adds a CI model-runtime check that deserializes all nine committed model artifacts and checks their model-card feature interfaces. This verifies artifacts in a clean CI checkout only; it does not prove that the deployed Streamlit process loaded those exact weights.

The existing live deployment smoke test checks HTTPS health and the Streamlit application shell only. A true live inference probe still needs a safe server-side diagnostic that reports build SHA, model ID, artifact hash, feature schema, source freshness and inference status without exposing user data.

## Kochi map and spatial evidence

- The provisional corporation outline contains a self-intersection and is not accepted as a legal boundary or coverage mask.
- The 2022 ward snapshot has 77 source polygons; three invalid geometries are excluded, leaving 74 contextual polygons. Six source records lack ward identifiers/names.
- A 2024 ward candidate does not reconcile cleanly to the current official ward register. No candidate is promoted as authoritative.
- ESA WorldCover 2021 is land-cover context, not a hazard map or a current/live layer. Esri satellite imagery is an interactive basemap mosaic, not real-time video.
- PR #102 changes the legend from visible hexadecimal strings to actual color swatches with plain-language descriptions. It does not repair source geometry or claim authoritative ward coverage.

Until an authoritative, current, licensed boundary/ward dataset is obtained and independently reconciled, display the partial ward layer only as contextual and do not calculate definitive ward-level exposure.

## Operational boundaries

The application may:
- explain registered hazards and compound scenarios;
- show source provenance, quality gaps and contextual spatial layers;
- run eligible research-model outputs with their limitations;
- provide deterministic preparedness and mitigation guidance;
- audit new observation panels and shadow predictions.

The application must not:
- issue official warnings or evacuation instructions;
- present reanalysis grid-point rainfall as a local street-level forecast;
- infer flood depth, inundation or damage from rainfall regression;
- treat unmonitored landslide sites or missing incident reports as non-events;
- claim that interventions reduced losses without causal outcome evidence;
- automatically promote a model based on a single holdout or drift monitor.

## Release gates still open

1. Restore GitHub Actions job creation and obtain real step logs.
2. Pass clean-checkout tests, provenance checks and model artifact deserialization.
3. Execute PR #101's targeted tests and full training; publish metrics only after a completed run.
4. Beat persistence and seasonal climatology on the untouched Kochi holdout with a positive paired confidence interval against both; then validate on independent station observations.
5. Acquire and adjudicate the Kochi flood panel and monitored landslide non-event panel.
6. Complete prospective shadow testing and hazard-owner review; operational clearance remains false.
7. Verify deployed model loading through a server-side inference diagnostic, not only HTTP health.
8. Obtain authoritative Kochi boundary/ward geometry or keep map coverage explicitly provisional.
9. Complete judge-facing demo and presentation with the above limitations clearly stated.

**Release status:** research prototype / competition demonstration candidate after UI and CI verification; not an operational early-warning service.
