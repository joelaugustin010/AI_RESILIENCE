# Multi-hazard model training status

Updated: 2026-10-30

## Work actually completed

- Recovered the existing `public-hydrology-source-bundle` GitHub Actions artifact (25 files, approximately 105 MB) for analysis.
- Audited the event/precipitation/metadata/catchment joins for the INDOFLOODS dataset.
- Trained a reproducible Random Forest research baseline to classify whether the peak level of an **already-recorded flood event** exceeded the gauge's published danger level.
- Used a gauge-grouped holdout so 39 test gauges were not used for training.

## Flood-event severity baseline results

- Usable labeled events: 4,451 from 153 gauges; 97 of 4,548 events lacked gauge danger-level metadata and were excluded.
- Train/test: 3,098 / 1,353 events; 114 train gauges and 39 held-out gauges.
- Test ROC-AUC: 0.646.
- Test balanced accuracy: 0.578.
- Test F1: 0.456.
- Majority baseline accuracy: 0.611; model accuracy: 0.615.

These results show only modest discrimination. This is **not** a validated flood forecasting model. INDOFLOODS contains recorded flood events, not matched non-flood periods, so it cannot train the probability of a flood occurring. The records are from Indian gauges generally and do not establish performance in Kochi.

## Ten-hazard readiness

| Hazard module | Current evidence / status | Training status |
|---|---|---|
| Flood | Kerala rainfall and river telemetry, INDOFLOODS event records, flood inventories; gauge datum, event/no-event labels and KSDMA raster semantics remain unresolved | Research event-severity baseline trained; no Kochi flood-occurrence model |
| Cyclone | IMD best-track archive exists; duplicate/suspicious rows and local impact labels need audit | Not trained |
| Earthquake | Regional USGS catalogue acquisition exists (92 records reported previously); too small and lacks local ground-motion/building-damage labels | Not trained; exact earthquake-time prediction is not a scientifically supported target |
| Landslide | GSI/KSDMA Ernakulam candidate polygons have three invalid source geometries | Not trained |
| Drought | Official drought portals/indices identified; no aligned Kochi target series confirmed | Not trained |
| Heatwave | Requires verified daily temperature/humidity and impact labels for the intended target | Not trained |
| Air pollution | KSPCB annual snapshots are not enough for time-varying source attribution | Not trained |
| Industrial incident | No verified local incident/exposure/meteorology training table confirmed | Not trained |
| Infrastructure failure | No asset-condition/failure history and service-dependency labels confirmed | Not trained |
| Compound disasters | Requires time-aligned joint event records and outcome labels; these are not yet validated | Not trained |

## Reproducibility

The training script is `scripts/train_flood_event_severity_baseline.py`. It reads the four INDOFLOODS tables from `data/external/raw/`, saves a model to `models/flood_event_severity_baseline.joblib`, and writes metrics to `reports/flood_event_severity_baseline.json`.

Source: Kuntla & Saharia, INDOFLOODS, Zenodo DOI 10.5281/zenodo.14584654. Dataset is described as openly accessible for academic/research purposes; cite the dataset and associated paper and observe original-source data policies.

**Safety gate:** Do not label all ten hazards “trained” or expose this baseline as a live warning model. Each hazard needs its own target, appropriate observations, leakage-resistant validation, calibration/uncertainty analysis, and independent validation before scientific prediction claims.
