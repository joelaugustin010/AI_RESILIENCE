# Independent spatial validation, calibration and shadow protocol

## Data contract

The evaluation command consumes an adjudicated CSV with exactly these required
fields (additional provenance columns are permitted):

- `split`: `train`, `calibration`, or `test`
- `spatial_group`: non-overlapping ward/catchment/station-region identifier
- `event_id`: stable storm, flood, landslide, outage or other event cluster ID
- `y_true`: independently adjudicated binary outcome (0/1)
- `probability`: frozen model probability generated without access to the label

The tool rejects spatial-group overlap and event IDs crossing partitions. Use
whole storm/event groups, not random rows. Keep test geography sealed until
the model and calibration method are frozen. Record data source, retrieval
date, licence, spatial reference system, event adjudication, missingness,
sensor uptime, and all transformations in a companion provenance manifest.

## Execution

```bash
python -m scripts.independent_validation --input adjudicated_holdout.csv --output reports/spatial_holdout.json
python -m scripts.independent_validation --input adjudicated_holdout.csv --output reports/spatial_holdout_platt.json --calibration platt
python -m scripts.independent_validation --input adjudicated_holdout.csv --output reports/spatial_holdout_isotonic.json --calibration isotonic
```

Platt scaling is fitted only on the separate calibration partition. Isotonic
regression is withheld unless at least 100 calibration rows and 20 examples
from each class are available; both methods also require 20 positives and 20
negatives. Report uncalibrated and calibrated scores on the same untouched test
set. Select calibration only on pre-registered calibration metrics, never by
choosing the best test result. Reliability bins are descriptive; include sample
counts and do not interpret empty/sparse bins as stable estimates.

Worst-location output is a stress diagnostic, not a ranking of wards when
sample sizes are tiny. Event-cluster bootstrap intervals resample whole events.
At least two clusters are needed for an interval; larger, hazard-specific
event counts and independent geographic coverage are required for any release
decision. The software deliberately never returns operational clearance.

## Prospective shadow mode

Use `append_shadow_record` to append frozen predictions with issue time,
input-as-of time, model ID/version, location, probability and input status to
an append-only JSONL audit log. Store subsequent adjudicated outcomes as a
separate, access-controlled outcome table joined by immutable prediction ID.
Never overwrite issued predictions after outcomes arrive. Shadow mode emits no
alerts and performs no automated actions. Monitor input freshness, missingness,
out-of-domain rate, inference latency, model exceptions, prediction
distribution, and delayed outcome completeness. Do not fit calibration on the
same period used for final shadow evaluation.

## Hazard-specific leakage rules

- Flood: group by flood event and catchment; predictors must be available at
  issue time. SAR footprints acquired after event onset are labels, not
  predictors. Tide and gauge observations must be timestamp-aligned and
  quality-flagged.
- Rainfall: hold out stations and time blocks; prevent neighboring station
  interpolation from leaking test observations into training.
- Cyclone: split by complete storm ID; all fixes/track points from one storm
  remain in one partition. Use only predictors available at forecast issue time.
- Earthquake aftershocks: define the mainshock time, forecast horizon and
  event window in advance; purge overlapping future-label windows and group
  by mainshock sequence.
- Landslide: distinguish monitored non-events from unknown/unobserved terrain.
  A monitored non-event requires sensor/inspection coverage over the target
  period; pseudo-absence must never be relabelled as confirmed absence.
- Drought: split by hydrological season and region; prevent rolling-window
  features from crossing split boundaries. Report meteorological, agricultural
  and hydrological drought as distinct targets.
- Industrial/infrastructure: split by facility/asset and operating time;
  include exposure time and censoring, not only incident rows.
- Compound hazards: group by the shared parent event and preserve temporal
  ordering; a component event in test cannot appear in training through a
  second hazard label.

## Interpretation

The tool is an evaluation harness. It does not supply missing observations,
establish that an external dataset is licensed or representative, or turn
research models into warnings. Synthetic data may be used for unit tests only,
never for benchmark scores or ground-truth claims.
