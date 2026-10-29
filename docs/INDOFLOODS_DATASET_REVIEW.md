# INDOFLOODS dataset review and audit

**Review date:** 2026-10-29  
**Source:** [INDOFLOODS on Zenodo](https://zenodo.org/records/14584655), DOI 10.5281/zenodo.14584654  
**Current status:** promising historical gauge-event evidence candidate; not yet a validated Kochi prediction dataset.

## Why this source matters

INDOFLOODS reports gauge-level flood-event start/end dates, peak flood levels, official warning/danger thresholds, gauge metadata, catchment characteristics, and event-scale precipitation. Its published record says the current version excludes the Ganga and Brahmaputra basins. The metadata preview includes Kerala gauges, so Kerala is represented in the metadata; the number of relevant gauges/events and whether any are close or hydrologically relevant to Kochi must be calculated from the complete files and independently checked.

This is more useful for outcome review than district-level event inventories, but the presence of flood events does not itself supply representative non-flood periods. The data cannot be used as a binary flood/no-flood dataset without a defensible definition and verified non-event observations.

## Registered files

The reproducible acquisition registry includes:
- `floodevents_indofloods.csv` — event periods and event-level flood characteristics.
- `metadata_indofloods.csv` — gauge locations, state/basin, warning/danger levels, coverage period, and source metadata.
- `catchment_characteristics_indofloods.csv` — catchment-scale physical and socio-environmental features.
- `precipitation_variables_indofloods.csv` — event-scale rainfall variables.

The acquisition workflow preserves raw bytes, computes SHA-256 and retrieval timestamps, and does not commit raw data by default. A new `scripts/audit_indofloods.py` reports schemas, missingness, duplicate rows, date coverage, coordinate screening, Kerala gauge IDs and explicit event-ID coverage checks. Tests cover missing files and prevent false claims about predictive validation.

## Hard limitations before any model training

1. Verify the paper's variable definitions and event extraction method.
2. Confirm the applicable licence. Zenodo describes access for academic and research purposes, but the inspected record did not clearly show an explicit licence. Keep attribution and do not redistribute until terms are clarified.
3. Verify each gauge's identity, location, basin and threshold definitions. Do not match an INDOFLOODS gauge to an NWDP station by similar name alone.
4. Confirm timestamps/time zone and the issue-time horizon. Event-scale precipitation windows may include rainfall during or after a flood and can leak the outcome if used for early-warning prediction.
5. A flood-event table contains positive events; absence of a row is not evidence of no flood. Obtain verified non-event periods with comparable monitoring coverage.
6. The station/catchment scale may not represent Kochi wards or urban drainage flooding. Spatial transfer must be justified rather than assumed.
7. Use event-grouped chronological holdout, a simple baseline and metrics with sample/event counts. Do not report accuracy or probability calibration until the data design supports them.

## Safe current use

Use this dataset first for source auditing, Kerala gauge coverage assessment, event-timing summaries and candidate crosswalk research. Keep the operational flood-prediction gate blocked until all target, timing, geographic, licence and evaluation requirements are met. An audit passing means the data structure is understood, not that a model predicts floods accurately.
