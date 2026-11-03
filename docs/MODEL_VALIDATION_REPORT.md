# Model validation report

**Status date:** 2026-11-02
**Overall finding:** The rainfall measurement method has a limited
chronological retrospective benchmark. None of the ten disaster-hazard or
consequence models has independent local historical validation or supports a
validated prediction.

| Workflow option | Mathematical/software checks | Historical validation | Prediction status |
|---|---|---|---|
| Flood | Rational Method units, input bounds, missing-duration behavior and runoff arithmetic tested. | No time/spatially matched flood impacts or verified drainage capacity. Separate rainfall measurement benchmark is not flood validation. | Flood prediction unavailable. |
| Cyclone | Wind conversion and `q=0.5 rho v²` checked against hand calculation; physical input bounds tested. NOAA IBTrACS v04r01 CSV schema/coordinate validation is tested separately. | No storm-track/landfall/wind damage matched event set. IBTrACS is not independent local consequence validation and is not integrated pending rights clarification. | Unavailable. |
| Earthquake | MMI integer bounds and qualitative mapping tested. | No verified local shaking/building impact set or site model. | Unavailable. |
| Landslide | Rainfall interval arithmetic, input limits and refusal to classify without a regional threshold tested. | No time-matched local rainfall/slope-failure catalog. | Unavailable. |
| Heatwave | NWS regression checked against the published 100 °F/55% example (rounds to 124 °F); domain/missing-input behavior tested. | No local co-located meteorology/health outcome set. | Unavailable. |
| Drought | SPI-1 distribution path, category output, minimum record length, duplicate/gap behavior and parser validation tested. | No eligible complete local 30-year station record plus independent drought outcomes. Existing snapshots are insufficient. | Unavailable. |
| Industrial incident | Matching-unit/averaging-period ratio and invalid comparison behavior tested. | No independent source-attributed release, monitoring and exposure outcome set. | Unavailable. |
| Infrastructure failure | Qualitative output contract and explicit missing dependency evidence tested. | No verified local dependency graph, failure/outage/repair records. | Unavailable. |
| Cyclone + flood | Separate components and unresolved interaction/no-addition behavior tested. | No synchronized cyclone/rain/river/coastal/flood/service outcome events. | Unavailable. |
| Heavy rainfall + drainage failure | Rational Method flow/capacity arithmetic, missing-capacity behavior and dynamic consequence output tested. | No verified local catchment, design capacity, drainage condition and observed flood outcomes. | Scenario hydraulic indicator only; impacts unavailable. |

## Retrospective rainfall measurement benchmark

The optional manual-rainfall evaluation predicts the next source-recorded
measurement when same-station observations are exactly one hour apart. It
uses a global chronological 80/20 timestamp split and a seven-day embargo:

- Training: 46,621 exact one-hour pairs.
- Held-out test: 11,675 pairs, 15 of 21 stations, 2012-06-22 through
  2014-12-31.
- Persistence baseline: MAE 3.9594 mm; RMSE 6.7252 mm.
- Training station-median baseline: MAE 3.0902 mm; RMSE 5.7189 mm.
- Gradient-boosting candidate: MAE 3.0221 mm; RMSE 5.2122 mm.

This is a single retrospective measurement benchmark, not a current forecast,
not independent storm-event validation, not flood validation, and not
consequence validation. The source copy contains no exact-zero rainfall
records, the time zone is undocumented, station event IDs are absent, and
coverage is partial. Lower errors on this split do not establish generalized
or operational superiority. See
`PHASE_4_VALIDATION_REPORT.md` for source details and the flood-classifier
readiness audit.

For complete dataset requirements, see `DATA_GAPS_AND_REQUIREMENTS.md`.
For dynamic scenario consequence semantics, see
`SCIENTIFIC_MODEL_DOCUMENTATION.md`.

Unit tests include synthetic values solely to test software arithmetic and
input handling. Those values are not stored as data, calibration evidence,
training examples, predictions, or scientific validation.

The earlier Phase 1B `src/historical_validation.py` readiness checker still
requires independent outcomes, source hashes, reviewed geographic/temporal
matching, feature cutoffs before outcomes, predeclared splits and error review.
No eligible validation case was submitted. Do not report accuracy, precision,
recall, calibration, false-positive rates, return periods or confidence from
these tests.

## Next validation protocol

For each hazard, predefine an observable target and event registry; obtain
independent ground-truth outcomes; establish the timestamp, timezone, spatial
matching tolerance and positional error; prevent post-outcome leakage; split
by event/time (and geography where possible); include non-event cases; report
case counts and uncertainty; review false positives/negatives; hash inputs and
version code; and have domain experts independently reproduce results.

Until that protocol is feasible, the correct status is **not validated**.
