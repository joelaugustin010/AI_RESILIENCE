# Shared ML engine — design and scientific boundaries

The shared engine exists so the project can use real supervised models without
duplicating preprocessing, leaking future information, or presenting weak
research baselines as validated predictions. It is deliberately small and
depends only on `scikit-learn`, `pandas`, `numpy`, `scipy` and `joblib`.

## Layers

| Module | Responsibility |
| --- | --- |
| `src/ml/data.py` | Builds datasets from tracked sources only; no downloads, no invented labels. |
| `src/ml/features.py` | Feature contract, target/future leakage guards, context validation. |
| `src/ml/estimators.py` | Deployment-compatible estimator factory. |
| `src/ml/evaluation.py` | Metrics, calibration diagnostics, bootstrap intervals, skill grading, 2×2 association. |
| `src/ml/training.py` | Temporal splits, threshold isolation, model selection, final fit, model-card construction. |
| `src/ml/persistence.py` | Atomic JSON and joblib persistence. |
| `src/ml/registry.py` | Model-card registry and consistency checks. |
| `src/ml/inference.py` | Fail-closed inference with an exact feature contract. |
| `src/ml/monitoring.py` | Training-range and missingness warnings. |
| `src/ml/coverage.py` | Evidence coverage for the exact ten workflow hazards. |
| `src/ml/service.py` | `ml_evidence_for(hazard, inputs)` boundary used by assessments and pages. |

## Temporal protocol

Every supervised model uses:

1. `train` — target dates before `validation_start`; event thresholds are
   estimated here only.
2. `validation` — used only for candidate comparison and probability-threshold
   selection.
3. `final_train` — train + validation, used for the final fit.
4. `test` — untouched until final scoring.

For grouped tracks (IBTrACS storms), a group crossing a boundary is assigned
wholly to the later split, so one storm cannot supply training rows and a test
row with the same track history. The exact split is stored in each model card.

## Skill grading

`NO_SKILL` and `INSUFFICIENT_TEST_EVENTS` models produce no decision output.
`WEAK_RESEARCH_SIGNAL` and `RESEARCH_SIGNAL_NOT_VALIDATED` models may produce a
clearly labelled research score when every required feature is supplied.
`EXPLORATORY_ASSOCIATION` is reserved for the concurrent compound model and is
withheld from inference. No status means validated.

Metrics include precision, recall, F1, ROC-AUC, average precision (PR-AUC),
Brier score, log loss, expected calibration error, confusion matrix, majority
and persistence baselines, and bootstrap intervals. A single chronological
holdout is still preliminary evidence.

## Coverage and missing models

The full ten-hazard matrix is in `reports/ml_disaster_coverage.json` and is
rendered in the Hazard Model Lab. Landslide, Industrial incident, and
Infrastructure failure have no released supervised model:

- the landslide source is a reported-event inventory with no representative
  non-event sample;
- the industrial source lacks quality-controlled release labels and controls;
- the infrastructure source lacks asset condition, dependency, outage and
  restoration labels.

These gaps are recorded rather than filled with synthetic negatives.

## Adding a model

1. Add a deterministic dataset builder with provenance and target naming.
2. Add a `TrainingConfig` with explicit temporal boundaries.
3. Declare predictors that are genuinely available at issue time.
4. Run the training script and inspect the model card.
5. Add the model to `HAZARD_MODEL_MAP` and the coverage interpretation.
6. Add tests for leakage, fail-closed inference and card consistency.
