# Empirical Validation Engine and Data Contracts — 2026-11-07

## Release boundary
The nine persisted models remain research artifacts. Synthetic data and simulation outputs cannot replace observed ground truth. This PR adds evaluation/monitoring tools but does not claim external datasets have been acquired or independently adjudicated.

## Phase 1 — Pipeline and deployment
PR #97 is merged. CI verifies model artifact integrity, model-card scope, HTTPS Streamlit health and application-shell availability. This PR adds `scripts/verify_model_runtime.py` to deserialize all nine committed model binaries in the CI environment, verify their inference interfaces and compare loaded feature counts with model cards. This is still a checkout-level check, not proof that the live Streamlit process loaded the same weights. A deployed inference probe still needs to expose a non-sensitive build SHA, model ID, artifact SHA-256, feature-schema hash, input source timestamps and inference status.

The shadow monitor computes KS statistics and PSI for numeric features, input-age and latency percentiles, source/model failure counts and a safe state. Drift is an alert, not permission to auto-swap models. A baseline fallback is eligible only when separately validated and explicitly approved; otherwise abstain and show deterministic preparedness guidance. Deployment rollback must be triggered by verified release-health failure and retain the last known-good release.

## Phase 2 — Observation data contracts
### Kochi flood event panel
One row per site × event × valid UTC observation time. Required fields: event_id, site_id, ward_or_catchment_id, latitude, longitude, observation_time_utc, rain_gauge_id, rain_mm_1h/6h/24h, river_gauge_id, river_level_m and river_datum, tide_station_id, tide_level_m and tide_datum, flood_observed, observed_depth_m, inundation_duration_h, SAR scene ID/acquisition time/processing version/footprint URI/quality, publisher, source record ID, license, acquisition time and adjudication status.

Join gauges, tide and SAR by UTC timestamps with a documented maximum offset; never carry a gauge across an event boundary. Preserve vertical datums. SAR water masks are uncertain observation proxies, not unquestioned truth; document revisit gaps, urban layover/double-bounce, geolocation error and validation against field/official records. Candidate sources: CWC/NWIC and Kerala/IMD gauges/rainfall, authorised port/oceanographic tide observations, Copernicus Sentinel-1 GRD, KSDMA/municipal incident reports. Do not mark a source acquired without checksum, schema/row audit, licence and acquisition manifest.

### Landslide non-events
Use repeated monitored site-periods with slope-unit geometry, survey dates/cadence, instrument coverage/downtime, rainfall, soil moisture and movement measurements where available, field inspection method/observer and explicit no-event adjudication. An unmonitored location is UNKNOWN, never a negative. Spatially block by slope unit and exclude adjacent pixels/sites across folds.

### Industrial and infrastructure
Facility records need authorised facility ID, operating state/hours, inspection coverage, incidents/near misses/releases, timestamps, severity and explicit non-incident operating periods. Infrastructure records need stable asset ID, fault onset, outage/restoration, maintenance, exposure and cause adjudication. Missing public reports are not negative labels; aggregate feeder metrics cannot label individual assets.

### External districts and interventions
Hold out complete districts/catchments/stations. Report leave-one-district-out and worst-district performance. Intervention evaluation needs site × event work footprints, commissioning and maintenance dates, treated/control status, rain/tide/exposure and measured depth/duration/damage. Pre-register estimands and account for targeting bias, pre-trends, concurrent works and spillovers. Sanctions or completion certificates alone do not prove impact.

## Phase 3 — Calibration and shadow
Run evaluate_independent_spatial_holdout.py on frozen predictions with partition, region_id, event_id, y_true, model_probability and baseline_probability. Calibration and test regions/events must be disjoint. Platt and isotonic calibrators are fit on calibration rows only; final test is untouched. Reports include pooled/per-region Brier, log loss, AUC, worst-region Brier and event-cluster bootstrap skill intervals. Isotonic is withheld below 100 calibration rows. Candidate review is only a screening step; operational clearance is always false until prospective shadow testing, hazard-owner review and warning governance pass.

The append-only shadow ledger should store issue time, model and feature hashes, source timestamps/status, input age, latency, prediction, region/event key and later adjudicated outcome timestamp. Never score an outcome that was known before prediction issue time.

## Phase 4 — Competition benchmark and evidence
Compare against persistence, climatology/base rate, matched official forecast products and transparent physical screening. Report event-level recall/precision, PR-AUC, false alarms per site-time, missed events, Brier/calibration, lead-time distribution, per-region and worst-region performance, event-cluster confidence intervals. Flood extent needs matched-time IoU, affected-area precision/recall, missed area and false-alarm area. Do not compare rainfall regression against a flood-warning target.

Each mitigation recommendation must include hazard pathway, local observation/source IDs, exposed asset/population, intervention, responsible owner, mechanism, evidence tier, maintenance, measurable outcome, evaluation design and caveat. Do not claim lives/money saved or causal effectiveness without suitable outcome data.

Judge-facing scope: AI_RESILIENCE is an evidence-gated multi-hazard decision-support prototype with deterministic scenario assessment, data/provenance audits, research ML outputs for selected hazards and preparedness guidance. It is not an independently validated Kochi early-warning system, does not issue official warnings, and does not estimate causal intervention effectiveness.


## Executable observation-panel audit

Run `python scripts/audit_observation_panel.py --kind flood --input <frozen_event_panel.csv>` or use `--kind landslide` for monitored site-period records. The audit checks required provenance fields, UTC timestamp offsets and monitored non-event requirements. Its output deliberately sets `training_ready=false`; a clean schema audit is not scientific adjudication or permission to train. It cannot validate the truth of a publisher's records or replace field review.


## GitHub Actions startup failure investigation (2026-11-07)

Runs 866 (PR #101), 868 (PR #99), 876 and 878 (PR #101), and 880 (PR #99) were inspected. The Windows test job and Ubuntu provenance job failed with no step records, no job log URL, and no downloadable log content (the log endpoint returned BlobNotFound). On PR #101, the independent Ubuntu rainfall-research job also failed with the same empty-step signature after it was detached from the full test job. Rerun requests were accepted but did not produce a step-level failure to diagnose.

The workflow was changed on PR #99 to use Ubuntu for the main test job and to cancel superseded branch runs; the same startup signature persisted. The PR #101 research job was made independently dispatchable and given its own compile and focused-test preflight, but the run still failed before steps began. This evidence does not support attributing the failure to Python dependencies, test assertions, or the training script. It is consistent with a GitHub Actions control-plane/runner-admission problem, but the exact platform-side reason is not exposed by the available run/job APIs. The billing usage summary previously reviewed did not establish that a budget limit was reached. Do not claim billing exhaustion or alter workflow/test code to mask this failure. Escalation to GitHub Support with run IDs and timestamps is required for internal platform diagnostics.
