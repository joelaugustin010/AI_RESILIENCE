# INDOFLOODS exploratory baseline results

**Run:** [GitHub Actions run 41426185431](https://github.com/joelaugustin010/AI_RESILIENCE/actions/runs/41426185431)  
**Artifact:** [indofloods-data-and-flood-baseline](https://github.com/joelaugustin010/AI_RESILIENCE/actions/runs/41426185431/artifacts/13131218785)  
**Status:** exploratory research only; not eligible for Kochi or operational integration.

## Dataset and governance

- Source: [INDOFLOODS, Zenodo record 14584655](https://zenodo.org/records/14584655), DOI 10.5281/zenodo.14584654.
- Only gauges explicitly marked `Open` in the dataset's `Privacy` metadata field were used.
- 4,451 recorded flood-event rows remained after joining event labels, open-gauge metadata and catchment attributes.
- 153 unique gauges; 1,629 events (36.6%) exceeded the gauge-specific danger level.
- Evaluation held out 39 entire gauges (1,353 events), so test gauges were not present in training.
- Event-scale `T1d`-`T10d` rainfall fields were deliberately excluded because their observation timing relative to event onset and a possible forecast issue time has not been verified.

## Holdout metrics

| Metric | Random Forest | Majority baseline |
|---|---:|---:|
| Accuracy | 0.540 | 0.611 |
| Balanced accuracy | 0.531 | 0.500 |
| Precision | 0.421 | — |
| Recall | 0.492 | — |
| F1 | 0.454 | — |
| ROC-AUC | 0.585 | — |

The classifier's accuracy is below the majority baseline. Its balanced accuracy and ROC-AUC are only modestly above chance. Five-fold gauge-grouped cross-validation was unstable: mean balanced accuracy 0.555 (standard deviation 0.135) and mean ROC-AUC 0.598 (standard deviation 0.124).

## Scientific interpretation

This experiment shows that static catchment characteristics alone have weak and inconsistent ability to distinguish danger-level exceedance among already-recorded events at previously unseen gauges. It does **not** predict flood occurrence, flood timing, water depth, inundation extent, or ward-level impacts. It is not a rainfall-to-flood model and does not establish Kochi/Ernakulam validity.

**Decision:** do not integrate this classifier into the live AI_RESILIENCE assessment or present its output as a probability or warning.

## Next evidence required

1. Obtain legally reusable, time-stamped gauge rainfall and river-level observations with known measurement intervals.
2. Define a prediction issue time and forecast horizon before selecting event rainfall features.
3. Obtain monitored non-event periods with known sensor uptime; no-event rows must not be fabricated from missing event records.
4. Identify hydrologically relevant gauges and catchments for the Kochi/Ernakulam area using verified gauge IDs, coordinates and basin connectivity.
5. Evaluate chronologically and by held-out gauge/event, compare with persistence and threshold baselines, and report uncertainty and missing-data coverage.
6. Add verified elevation, drainage, tide/backwater and urban flood evidence before making ward-scale flood-impact claims.

Until those conditions are met, use this dataset for historical event summaries and source-verified catchment context only.
