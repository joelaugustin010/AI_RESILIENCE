# Kochi flood event-panel ML pipeline

This is the first implemented Kochi-specific flood research pipeline. It
provides strict event-panel ingestion, label quality control and a future-event
research baseline. It does not create live flood forecasts or alter warning
status in the Decision Workflow.

## Included
- Site-by-event schema with issue, feature and later outcome timestamps.
- Feature timestamps must be no later than issue time.
- Dry labels require explicit verified observation coverage; missing imagery
  is never treated as a non-event.
- Chronological holdout keeps whole events together.
- Logistic-regression baseline reports precision, recall, F1, ROC-AUC,
  Brier score, confusion matrix and training-prevalence Brier reference.
- Small panels and single-class splits are blocked.
- No model artifact is saved; operational prediction remains disabled.

## Required CSV columns
event_id, site_id, issue_time, feature_time, outcome_time,
inundation_observed, negative_observation_verified, observation_source_id,
observation_coverage, rainfall_24h_mm, rainfall_72h_mm, river_level_m,
tide_level_m.

Use one fixed, documented outcome window. The source manifest must separately
record sensor, acquisition time, CRS, footprint, quality mask, licence,
processing version and reviewer. Gauge station and datum must be documented.
Do not silently impute missing sensor records.

## Run
python scripts/audit_kochi_flood_event_panel.py path/to/verified_panel.csv
python scripts/audit_kochi_flood_event_panel.py path/to/verified_panel.csv --evaluate

Evaluation requires at least 10 training events, 5 future test events, 3
sites and both classes in each temporal partition. These are minimum
engineering gates, not proof of statistical sufficiency.

## Acquisition still required
1. Acquire NRSC/ISRO flood extent records and/or Sentinel-1 SAR scenes for
   documented Kochi/Ernakulam events.
2. Derive inundation masks with acquisition-specific quality control and
   independent review.
3. Match sites and times to rainfall, CWC river gauges and tide observations,
   retaining source timestamps, station identity, units and datum.
4. Create dry observations only where valid imagery covers the site and
   outcome window.
5. Add geographically held-out site evaluation before any operational claim.

Until a verified local panel exists and independent evaluation succeeds,
Kochi flood prediction remains not validated. Follow KSDMA, IMD and district
administration guidance during actual emergencies.
