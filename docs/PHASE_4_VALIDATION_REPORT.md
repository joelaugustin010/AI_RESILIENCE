# Phase 4 validation report

**Review date:** 2026-11-02
**Overall status:** The rainfall measurement model has a reproducible
chronological historical benchmark. No disaster-impact predictor has
independent local validation. Every hazard's predictive status remains
**NOT YET VALIDATED**.

## Historical rainfall measurement benchmark

The optional benchmark in `src/rainfall_forecast.py` was run against the
existing manual rainfall source file. It predicts the next source-recorded
measurement only when consecutive records at a station are exactly one hour
apart. It is not a current forecast or a flood model.

| Evaluation item | Result |
|---|---|
| Source rows | 109,978 |
| Stored timestamp coverage | 2000-02-27 21:30 through 2014-12-31 17:30 |
| Source filename claim | Filename indicates 1991-2020; observed records in this local copy do not match that span |
| Unique timestamp split | Global chronological 80/20 split |
| Temporal embargo | 7 days |
| Training pairs | 46,621 exact one-hour pairs |
| Test pairs | 11,675 exact one-hour pairs |
| Test period | 2012-06-22 14:30 through 2014-12-31 13:00 |
| Test station coverage | 15 of 21 stations |
| Outcome | Next source-recorded manual rainfall amount, mm |

| Method | Test pairs | MAE (mm) | RMSE (mm) |
|---|---:|---:|---:|
| Persistence (previous-hour reading) | 11,675 | 3.9594 | 6.7252 |
| Training station median | 11,675 | 3.0902 | 5.7189 |
| Gradient-boosting candidate | 11,675 | 3.0221 | 5.2122 |

These are descriptive out-of-time errors for this source and split only. The
gradient-boosting candidate has lower measured errors on this holdout, but the
single split, no event identifiers, unknown time zone, lack of independent
event grouping, incomplete station coverage, and absence of exact-zero
rainfall records preclude a claim of generalization or superiority. There is
no uncertainty interval, calibrated probability, or flood outcome label.
Model outputs are historical reconstruction for methodology review only.

## Flood classifier readiness

`src/flood_model.py` was audited against the actual candidate
`data/raw/disaster_probability_data.csv`. It contains five rows (two label-0
and three label-1 records) on one distinct date. The evaluation gate refused
the data. Blockers include:

- Fewer than the code's prototype screen of 100 rows and 20 records per class.
- One date, so no chronological split is possible.
- Missing event-group identifiers, so related events cannot be separated.
- No documentation that the file contains verified real observations or
  independently reviewed labels.
- Missing required publisher, source URL, retrieval date, licence, geographic
  coverage, label definition/source/review, feature cutoff, time zone and
  prediction-horizon provenance.
- Potential target leakage from warning/gauge fields whose availability time
  is undocumented.

These numeric screening floors are implementation gates, not universal
scientific adequacy criteria. No model was fit and no flood probability was
computed.

## Hazard-specific validation status

| Workflow selection | Historical event/outcome validation | Metrics reported | Status |
|---|---|---|---|
| Flood | No independent, spatial/time-matched inundation or impact outcome set. The rainfall benchmark is not flood validation. | None for flood prediction. | **NOT YET VALIDATED** |
| Cyclone | No matched track, landfall, local wind/surge, exposure and damage set. | None. | **NOT YET VALIDATED** |
| Earthquake | The regional USGS query returned zero features; no local shaking/building outcome set. | None. | **NOT YET VALIDATED** |
| Landslide | No georeferenced local failures joined to time-aligned rainfall and terrain. | None. | **NOT YET VALIDATED** |
| Heatwave | No co-located meteorology, health outcomes, and independent local warning labels. | None. | **NOT YET VALIDATED** |
| Drought | No eligible homogeneous, complete 30-year local monthly reference series plus independent impacts. | None. | **NOT YET VALIDATED** |
| Industrial incident | No independently source-attributed release, emissions, meteorology, monitoring and exposure outcomes. | None. | **NOT YET VALIDATED** |
| Infrastructure failure | No owner-verified asset topology or failure/outage/repair/service-impact history. | None. | **NOT YET VALIDATED** |
| Compound: cyclone + flood | No synchronized cyclone, rain, river/coastal water, drainage, flood footprint and service-impact events. | None. | **NOT YET VALIDATED** |
| Compound: heavy rainfall + drainage failure | No surveyed catchments/drainage capacity plus time-matched rainfall and observed inundation outcomes. | None. | **NOT YET VALIDATED** |

Unit tests for equations, input contracts, parsing, edge cases and reference
calculations are software checks, not historical validation. Synthetic test
fixtures are used only to test software and are not project observations,
training data, or model performance evidence.

## Spatial data validation relevant to consequences

Read-only checks using `src/spatial_data.py` and the existing metadata gave:

- `data/reference/kochi_corporation_boundary.geojson`: one polygon, provenance
  fields present, but invalid due to a self-intersection between ring segments
  699 and 701. It is not a valid exposure-analysis mask.
- `data/processed/spatial_layers/kochi_wards_datameet_2022.geojson`: 74
  polygons, no invalid feature, duplicate feature, or missing-property issue
  found by the local check. Source metadata still records three invalid source
  polygons excluded and six source rows without ward identifiers; the
  community-repackaged layer is not an authoritative/current hazard boundary.
- NIHFW Ernakulam hospital coordinate review: 180 rows, 31 missing/nonnumeric
  coordinate pairs, 18 duplicate coordinate-pair groups covering 63 rows.
  CRS, coordinate order and positional accuracy are unresolved; no points are
  used for exposure sampling.
- KSDMA flood raster meaning/reuse terms, population distribution, verified
  drainage/utility networks and current owner-confirmed asset locations remain
  unavailable or unsuitable.

No exposure metrics, spatial overlap scores, vulnerability rankings or
casualty/economic estimates were calculated.

## Reproducibility and next validation gate

The rainfall benchmark uses a fixed random state, global chronological
split, explicit seven-day embargo, exact one-hour pairs, no interpolation, and
the raw local source rows. It is reproducible with
`.venv\Scripts\python.exe -m pytest -q test_rainfall_forecast.py` and the
existing "Run the historical holdout evaluation" control. The raw source is
not modified. Pin source hashes, provider timezone, event grouping, station
metadata, and an independent later dataset before operational evaluation.

For each hazard, predefine target and horizon; obtain independent outcomes;
review time and geographic matches; exclude post-issue features; split by
event/time and, where possible, geography; compare prespecified baselines;
report sample/coverage and false positives/negatives; and obtain independent
domain review. Do not compute classification, calibration, spatial, or impact
metrics before the relevant matched data exist.
