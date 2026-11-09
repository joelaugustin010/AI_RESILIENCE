# Observed disaster-impact validation

This evaluation path compares pre-generated model predictions with observed,
source-linked impact records. It does not train a model and cannot certify
operational validity by itself.

## Required holdout table

Start from data/templates/observed_impact_holdout_template.csv. One row must
represent one consistently defined outcome for one geography during one
observed event.

Required fields:
- observation_id: unique row key;
- event_id: independently documented event identifier;
- geography_id: stable ward/asset-area identifier;
- observation_date: date of the observation;
- outcome_name: one outcome only, such as affected_people or damaged_buildings;
- outcome_value: observed value from the source record;
- predicted_value: frozen model prediction made before outcome review;
- outcome_unit: persons, buildings, INR, hours, or another explicit unit;
- source_url: HTTPS reference to the observed outcome source.

Do not mix exposed population, affected people, displaced people, casualties,
and damaged buildings. Do not use the same event or geography in training and
holdout. Do not derive ground truth from the model prediction itself.

## Provenance metadata

The JSON sidecar must include model_id, model_version, outcome_definition,
outcome_unit, training_event_ids, training_geographies, ground_truth_source,
prediction_method and known_limitations. The evaluator blocks event or
geography overlap, missing provenance, inconsistent outcome definitions,
invalid numeric values, and too few independent events/geographies.

## Run

PowerShell command:
python scripts\evaluate_observed_impact_holdout.py --holdout data\local\observed_impact_holdout.csv --metadata data\local\observed_impact_model_metadata.json

The evaluator reports MAE, RMSE, bias, median absolute error, percentage
errors where defined, aggregate prediction-to-observation ratio and
event-level error. It requires at least three holdout events and two holdout
geographies by default.

A passing result is labelled HOLDOUT_EVALUATED_NOT_VALIDATION_CERTIFIED.
Independent replication, source-quality review, calibration assessment and
domain-expert approval remain necessary. This is not a causal-effect
evaluation and it does not convert population exposure into actual affected
population.
