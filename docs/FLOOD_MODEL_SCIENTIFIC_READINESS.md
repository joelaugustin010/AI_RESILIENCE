# Flood-model scientific readiness review

**Review date:** 2026-10-29  
**Scope:** The repository's candidate flood-classification dataset and the conditions required before claiming real-world predictive performance.  
**Decision:** **NOT READY for flood prediction or scientific model evaluation.** Do not present the current model as a calibrated probability or operational early-warning system.

## Findings from the repository

The current `data/raw/disaster_probability_data.csv` contains only five rows, all dated 2026-10-19. Its sidecar `data/reference/disaster_probability_data.metadata.json` explicitly marks it `unverified_demo`, with no source URL, publisher, licence, geographic coverage, target definition, label source, event grouping, prediction issue-time cutoff, or prediction horizon. The sidecar says the rows are illustrative and not representative.

The five records cannot support a defensible train/test split, calibration, precision/recall claims, or generalisation to Kochi. The CSV's target labels are not independently verified. The fields `cwc_flood_warning_level`, `river_gauge_height_m`, and `danger_level_m` could leak information about the outcome unless their observation and publication times are shown to precede the prediction issue time.

The existing `src/flood_model.py` readiness gate is intentionally fail-closed. Its synthetic test fixture tests pipeline mechanics only; any metrics from it are **not evidence of flood-prediction skill**. Keep this distinction in the UI and exhibition explanation.

## Relevant public evidence already inventoried

1. **Kerala Surface Water Department hourly rainfall, 1991–2020** — NWDP catalogue: https://nwdp.nwic.gov.in/en/dataset/rainfall-manual-hourly-kerala-sw-department  
   The repository's local copy has observations from 2000-02-27 to 2014-12-31, irregular intervals and long gaps. It has no station-level flood outcome labels. It can support rainfall description/quality checks, not by itself a labelled flood classifier.

2. **CWC Kerala hourly telemetry rainfall, 2021–2025** — NWDP catalogue: https://nwdp.nwic.gov.in/dataset/rainfall-cwc-telemetry-hourly  
   The local `data/raw/kerala.csv` has not been checksum-matched to the catalogue download. The current audit records 1,471 duplicate station-time groups, 324 conflicting; do not silently deduplicate or aggregate these. There are no station-level flood outcome labels in this file.

3. **Kerala Surface Water Department river-level resources** — examples in NWDP include manual and telemetry hourly water-level catalogues. These need source-file checksum, station identity, gauge datum/reference, units, timezone and warning-threshold review before being joined to rainfall. The current inventory records unresolved datum/reference questions and inconsistent river/basin labels for some rows.

4. **KSDMA official flood-event documentation** — https://sdma.kerala.gov.in/floods_2018/ and event-specific maps at https://sdma.kerala.gov.in/event-specific-maps/  
   These establish historical event context and provide maps/reports, but a state- or district-level declaration is not a station-time label. Do not assign a flood/no-flood label to every hourly record in a district just because an event occurred during that period.

5. **IMD API reference** — https://api.imd.gov.in/public/api_reference.html  
   The public reference documents forecast endpoints, including basin quantitative precipitation forecasts. Forecast products may be useful as input only when their issue time and valid time are preserved; current forecasts cannot retrospectively substitute for archived forecasts.

6. **CWC appraisal report** — https://cwc.gov.in/sites/default/files/appraisal-report-2024-publicationcompressed.pdf  
   CWC describes operational forecasting inputs including rainfall products, IMD forecasts and river observations. This supports the need to align multiple time-stamped hydrometeorological sources; it does not validate this repository's model.

7. **INDOFLOODS gauge-event dataset** — https://zenodo.org/records/14584655  
   The dataset contains gauge-level flood event periods, warning/danger thresholds, gauge metadata, catchment characteristics and event-scale precipitation. Its metadata includes Kerala gauges, making it a candidate for event/outcome review. The full audit must determine coverage and event counts, and no gauge may be joined to NWDP data by name alone. Event-scale precipitation may include rainfall during/after an event and cause leakage. The flood-event table does not provide representative non-event periods by itself. See `docs/INDOFLOODS_DATASET_REVIEW.md`.

## Required data before a real model can be evaluated

Build a provenance-preserving, station-time table with (where available):

- observed rainfall and its timestamp, station ID, units, source and quality flags;
- archived forecast rainfall with issue time, valid time, lead time and source;
- river level/discharge with station ID, documented gauge datum, official warning/danger levels and timestamp;
- independently sourced flood outcomes with a clear spatial unit, time interval, definition, evidence source and review status;
- event IDs to group records belonging to the same flood event;
- station metadata and spatial matching evidence, with CRS/datum and positional accuracy documented.

A target definition must be agreed before joining data. For example, a station/catchment flood outcome in a stated future window is not interchangeable with a district-wide government declaration. Do not manufacture negative labels from missing reports or label all hours during an event as positive.

## Evaluation protocol

1. Preserve downloaded source files unchanged; record source URL, provider, retrieval time, licence/reuse terms, checksum, coverage, units, timezone and limitations.
2. Validate schema, timestamps, units, missingness, duplicate/conflicting station-time keys and station identity. Investigate conflicts rather than averaging them away.
3. Freeze the prediction issue time and prediction horizon; exclude any feature not actually available at that issue time.
4. Keep related stations/time windows from the same event grouped to avoid event leakage. Use chronological holdout and, where feasible, leave-one-event-out evaluation.
5. Compare with a simple baseline. Report sample counts, event counts, class balance, precision, recall, F1, confusion matrix and uncertainty; use calibration metrics only with sufficient independent data.
6. Do not tune on the final holdout. Document all exclusions and rerun the whole suite from a clean checkout.
7. Only consider a predictive claim if enough independently verified, representative events and non-events exist and the held-out evaluation supports it. A passing software test suite is not scientific validation.

## Safe deliverable for the exhibition today

Until these data requirements are met, present the flood module as a **data-readiness and historical-risk evidence dashboard**, not as a predictor. It can show sourced rainfall summaries, data-quality warnings, official historical event context and transparent limitations. Any manually entered scenario must be labelled as a hypothetical scenario, not a probability forecast.

**Current status:** Data-readiness gate = blocked. INDOFLOODS is now registered for provenance-preserving acquisition and descriptive gauge/event auditing, but it has not yet been established as a suitable Kochi training/evaluation dataset. Verified representative non-event periods, exact gauge crosswalks and a leakage-safe prediction horizon remain unresolved. Operational flood prediction = not validated.
