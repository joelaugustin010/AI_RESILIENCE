# Persisted shared ML model catalog — 2026-11-07

This release stores the artifacts produced by the shared research retraining workflow in `models/ml/` so the Streamlit application can discover and load the same model versions that were evaluated in CI.

## Persisted artifacts

Each registered model directory contains a `model.joblib` binary and a `model_card.json` record:

- `weather_extreme_rainfall_kochi_nextday`
- `weather_high_temperature_kochi_nextday`
- `weather_drought_onset_kochi_30day`
- `cyclone_rapid_intensification_24h`
- `earthquake_aftershock_occurrence`
- `compound_cyclone_rainfall_interaction`
- `weather_precipitation_kochi_nextday_regression`
- `weather_tmax_kochi_nextday_regression`
- `cyclone_wind_change_24h_regression`

The corresponding registry, coverage, and validation summaries are stored in:

- `reports/ml_model_registry.json`
- `reports/ml_disaster_coverage.json`
- `reports/ml_validation_report.json`

## Scientific and operational boundary

These are reproducible trained research artifacts, not nine independently validated disaster-warning systems. Their model cards remain authoritative for task-specific readiness, metrics, data scope, baseline comparisons, and limitations. In particular:

- A retrospective weather or best-track estimate must not be presented as a live hazard warning.
- A research score is not a calibrated probability of local disaster impact.
- The compound cyclone/rainfall model is an exploratory concurrent association, not a lead-time forecast or causal estimate.
- Landslide, industrial incident, and infrastructure failure remain without defensible supervised models because the required event/non-event training panels are unavailable.
- The app must continue to use the shared inference service and its evidence/readiness gates; do not load these binaries directly in page code or bypass model-card status checks.

Retraining is performed by `scripts/train_shared_ml_models.py`. Any change to source data, target definition, feature set, split, or threshold requires a fresh evaluation and updated model cards before the artifacts are replaced.
