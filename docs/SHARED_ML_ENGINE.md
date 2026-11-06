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
| `src/ml/training.py` | Temporal splits, threshold isolation, classification model selection, final fit and model-card construction. |
| `src/ml/regression.py` | Continuous next-day rainfall and temperature regression, validation-only estimator selection, persistence/median baselines and MAE/RMSE/R². |
| `src/ml/persistence.py` | Atomic JSON and joblib persistence. |
| `src/ml/registry.py` | Model-card registry and consistency checks. |
| `src/ml/inference.py` | Fail-closed inference with an exact feature contract. |
| `src/ml/monitoring.py` | Training-range and missingness warnings. |
| `src/ml/coverage.py` | Evidence coverage for the exact ten workflow hazards. |
| `src/ml/service.py` | `ml_evidence_for(hazard, inputs)` boundary used by assessments and pages. |
| `src/intervention_effectiveness.py` | Doubly-robust, site-group-cross-fitted observational intervention-effect research, with chronological holdout, overlap gates, site-cluster bootstrap and fail-closed ranking. |

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

Classification metrics include precision, recall, F1, ROC-AUC, average precision (PR-AUC), Brier score, log loss, expected calibration error, confusion matrix, majority and persistence baselines, and bootstrap intervals. Regression metrics include MAE, RMSE and R² against persistence and training-median baselines. A single chronological holdout is still preliminary evidence.

## Coverage and missing models

The full ten-hazard matrix is in `reports/ml_disaster_coverage.json` and is
rendered in the Hazard Model Lab. The Drought model is currently invalidated because its previous target construction overlapped historical rainfall features. The Earthquake aftershock model is also invalidated because the old seven-day future label windows could cross temporal split boundaries. Their old metrics are superseded and inference is blocked until corrected retraining.
Landslide, Industrial incident, and Infrastructure failure have no released supervised model:

- the landslide source is a reported-event inventory with no representative
  non-event sample;
- the industrial source lacks quality-controlled release labels and controls;
- the infrastructure source lacks asset condition, dependency, outage and
  restoration labels.

These gaps are recorded rather than filled with synthetic negatives.

## Continuous ML conversion

The shared workflow also trains next-day continuous rainfall and maximum-temperature regressors, plus a 24-hour cyclone wind-change regressor from IBTrACS best-track sequences. Candidate estimators are selected using validation MAE only; the final test period is untouched until scoring. A model is eligible for research inference only when it beats the persistence MAE baseline. These estimates are weather components, not direct flood or heat-health predictions. The same feature contract, registry, artifact persistence, service boundary and Hazard Model Lab display are used; no parallel ML framework is introduced.

## Adding a model

1. Add a deterministic dataset builder with provenance and target naming.
2. Add a `TrainingConfig` with explicit temporal boundaries.
3. Declare predictors that are genuinely available at issue time.
4. Run the training script and inspect the model card.
5. Add the model to `HAZARD_MODEL_MAP` and the coverage interpretation.
6. Add tests for leakage, fail-closed inference and card consistency.


## Outcome-window boundary purging

A temporal split must account for the full period used to construct each label,
not only the event's issue/anchor date. For forward-looking labels, a row whose
outcome window crosses a validation or test boundary is excluded from the
earlier split. The aftershock dataset records `target_window_end` (seven days
after the observed mainshock), and the training engine purges rows whose label
window reaches into the next split. This prevents a training-era label from
depending on catalogue events that belong to the validation or test era.

This embargo is distinct from storm-group purging. Both controls are recorded
in split metadata. The aftershock model must be retrained after this change;
its previous holdout metrics are not valid evidence for the purged protocol.


## Preventive action intelligence

The shared `src/prevention_intelligence.py` module converts registered hazard selections
and user-supplied context into practical preparedness and mitigation options for both
the general Decision Workflow and the specialized compound workspace. Each item carries
a phase, hazard, activation trigger, intended benefit, responsible party, evidence needed
and safety caveat. Registered hazards have hazard-specific action templates; compound
selections expand into their component hazards; nominated critical services add continuity
checks; entered rainfall and river values add provenance checks rather than invented
warning thresholds.

The action engine deliberately does **not** predict whether an action will work at a
specific site, calculate lives or money saved, estimate percentage risk reduction, rank
actions, or issue evacuation instructions. It distinguishes routine preparedness from
actions that depend on an official warning. Local authorities, qualified engineers,
health services and utility operators remain responsible for site-specific decisions.
Unregistered custom scenarios receive a specialist-review prompt rather than fabricated
hazard-specific advice. These recommendations are a preparedness layer alongside the
scientific models, not ML predictions or a replacement for them.


## Intervention-effectiveness ML

The separate `src/intervention_effectiveness.py` engine estimates the effect of
one registered precaution against no implementation on a comparable numeric
damage-severity outcome. It uses cross-fitted propensity/outcome nuisance
models, doubly-robust pseudo-outcomes, a CATE learner, a chronological holdout,
treatment-overlap gates and site-cluster bootstrap uncertainty. Stable action
IDs from `src/prevention_intelligence.py` join action definitions to outcome
records. The Decision Workflow and compound workspace show a ranking only
when eligible models exist and share a hazard, outcome unit, feature contract
and test period.

No real, provenance-verified intervention episode dataset is currently
registered. Consequently the training CLI is implemented but no action-effect
model has been trained from real observations; the application must show
`RANKING_WITHHELD`. Synthetic data is allowed only in isolated software tests,
never as training evidence or as a reported risk-reduction estimate. See
`docs/INTERVENTION_EFFECTIVENESS_ML.md` for the schema, estimand, assumptions,
limitations and training command.
