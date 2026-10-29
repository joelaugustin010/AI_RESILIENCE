# Nine non-flood hazard models: data and training status

This document is deliberately conservative. A source link is not a downloaded dataset, and an event catalogue is not a predictive model.

## Hazard-specific source registry
The machine-readable registry is `data/external/hazard_dataset_registry.json`. It records nine candidate hazard tracks, authoritative source portals, potential targets, and critical limitations.

## What is implemented
- A versioned source registry for earthquake, tropical cyclone, landslide, drought, extreme heat, wildfire, tsunami, severe storm/extreme rainfall, and air-quality episodes.
- `scripts/audit_hazard_datasets.py`, which checks whether local CSVs have a target label, multiple classes, enough rows/groups for review, time information, and candidate predictors.
- A machine-readable readiness report at `reports/hazard_dataset_readiness.json` when the audit is run.

Run:
```bash
python scripts/audit_hazard_datasets.py
```

Place curated, source-documented CSVs in `data/external/hazards/<hazard_id>.csv`. The required target column is `target`; include a group identifier such as `event_id`, `storm_id`, `station_id`, or `location_id`, plus a timestamp. Keep a separate provenance manifest for each source, including retrieval date, publisher, licence, units, spatial coverage, temporal coverage, and transformations.

## Why the nine models are not marked trained yet
No valid training data can be inferred from source URLs or event-only catalogues. A defensible model needs (1) a defined target and forecast horizon, (2) predictor values that would have been available at prediction time, (3) representative positive and negative/background periods or validated outcome labels, (4) geographic/time-aware holdout evaluation, and (5) metrics compared with a simple baseline. Without these, training would create misleading outputs.

The earthquake and tsunami tracks are especially unsuitable for claims of short-term occurrence prediction from event catalogues alone. Cyclone tracks need storm-held-out testing and forecast-time predictors. Landslide/wildfire inventories require defensible background samples and bias analysis. Heat, drought, extreme-rainfall, and air-quality models require aligned time series and future-time splits.

**Safety boundary:** these are research prototypes only, not emergency alerts, official forecasts, or validated Kochi/Ernakulam predictions. Do not present a readiness audit or a trained generic model as operationally reliable.
