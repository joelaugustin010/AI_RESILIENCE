# Shared supervised ML deployment review — 2026-11-07

## Artifact persistence

The shared-ML training workflow completed successfully and committed the generated research artifacts to this branch in commit `d69f79f668b7e1a55a411340fad9607d58d812a5`.

The committed registry contains nine trained model artifacts (six classifiers and three regressors), each with a model card:

- `weather_extreme_rainfall_kochi_nextday`
- `weather_high_temperature_kochi_nextday`
- `weather_drought_onset_kochi_30day`
- `cyclone_rapid_intensification_24h`
- `earthquake_aftershock_occurrence`
- `compound_cyclone_rainfall_interaction`
- `weather_precipitation_kochi_nextday_regression`
- `weather_tmax_kochi_nextday_regression`
- `cyclone_wind_change_24h_regression`

The persisted reports are `reports/ml_model_registry.json`, `reports/ml_validation_report.json`, and `reports/ml_disaster_coverage.json`.

## Evidence and maturity

- The generated validation report records six classifiers and three regressors trained.
- The report records **zero independently validated operational models**.
- All nine models are single-temporal-holdout research artifacts, not operational warnings.
- Classification probability calibration is not consistently better than base-rate references; model cards retain weak/exploratory statuses where appropriate.
- Regression models show holdout improvement over their stated baselines, but remain research signals pending independent validation.
- Flood-related weather outputs are rainfall forcing evidence, not flood occurrence, inundation depth, or impact predictions.
- The compound cyclone/rainfall classifier is concurrent exploratory association without forecast lead time or joint-probability interpretation.
- The aftershock model applies only after an observed mainshock; it does not predict mainshocks or ground shaking.
- Landslide, industrial incident, and infrastructure failure have no defensible supervised model because the required representative labels and non-event/asset histories are not available.

## Hazard coverage

All ten workflow hazards remain selectable and represented in the coverage report. Seven have at least one trained model card or component research signal; only four have a hazard-specific usable research model. Coverage must not be described as predictive validity.

## Release gate

Do not promote any model to an operational warning or claim the platform is independently validated. Keep deterministic/evidence-based assessments and precaution guidance available, clearly separate from research-model outputs. Release requires the exact persisted-artifact revision to pass the full test suite, model-loading/inference checks, and live application verification.
