# ML scientific audit and remediation backlog

**Audited snapshot:** PR #82, commit `1dd4d402a99469c0cd416d629caeff5f9c7f0d4b`  
**Date:** 2026-11-06

## Conclusion

The shared ML engine is a useful research foundation, but none of the six models is independently validated for operational use. All six use a single chronological holdout; no model has a demonstrated independent geographic holdout. The ten-hazard registry is a coverage map, not evidence that ten hazards have predictive models.

Do not use model scores as official warnings, evacuation triggers, damage estimates, casualty estimates, or calibrated probabilities of harm. Deterministic evidence-based assessment and official agency guidance remain authoritative.

## Existing holdout results

Metrics below are copied from PR #82 model cards. They describe one temporal test period only.

| Model target | Test rows / events | Prevalence | Precision | Recall | F1 | PR-AUC | Brier | Base-rate Brier | Persistence F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Kochi next-day extreme rainfall | 2,192 / 153 | 6.98% | 0.387 | 0.471 | 0.425 | 0.358 | 0.0888 | 0.0649 | 0.425 |
| Cyclone rapid intensification, 24 h | 1,753 / 86 | 4.91% | 0.298 | 0.163 | 0.211 | 0.247 | 0.0537 | 0.0467 | 0.240 |
| Kochi next-day high temperature | 2,192 / 224 | 10.22% | 0.709 | 0.781 | 0.743 | 0.756 | 0.0695 | 0.0917 | 0.692 |
| Kochi 30-day rainfall-deficit proxy | 2,221 / 36 | 1.62% | 0.967 | 0.806 | 0.879 | 0.941 | 0.00338 | 0.01595 | 0.861 |
| Earthquake aftershock sequence proxy | 156 / 93 | 59.62% | 0.831 | 0.796 | 0.813 | 0.912 | 0.1570 | 0.2408 | Not recorded |
| Concurrent cyclone / extreme-rain association | 2,192 / 153 | 6.98% | 0.418 | 0.529 | 0.467 | 0.418 | 0.1378 | 0.0649 | 0.425 |

### Model-by-model findings

- **Extreme rainfall:** Target is next-day rainfall at one Kochi reanalysis grid point above a training-period 95th-percentile threshold (28.7 mm), not observed flooding. F1 is effectively identical to persistence; Brier is worse than the base-rate reference. Keep as weak rainfall-forcing evidence only.
- **Cyclone rapid intensification:** Target is a >=30 kt wind increase over approximately 24 hours from IBTrACS best-track history. Best-track reanalysis is post-event, not an operational forecast input. F1 is below persistence and Brier is worse than base rate. Only 86 test events.
- **High temperature:** Target is next-day Tmax above a 31.9 °C training-period percentile threshold, not an official IMD heatwave label. F1 and Brier beat the listed references on this holdout, but this is one reanalysis grid point; humidity, night-time temperature, consecutive-day criteria, station normals and exposure are absent.
- **Drought:** Target is next-30-day rainfall sum <=5.7 mm at the Kochi grid point, not agricultural or hydrological drought. Only 36 test events (1.62% prevalence). F1 is only modestly above persistence. High PR-AUC and low Brier are encouraging for this narrow proxy but do not validate a drought model.
- **Earthquake aftershock:** Target is whether an observed M>=5 event is followed by a nearby M>=4 event within 50 km and seven days. It is not earthquake prediction. The test set has 156 rows; the regional USGS catalogue is capped at 20,000 events. No persistence baseline was recorded. **A label-window defect was identified:** splitting by mainshock time allows a seven-day future outcome window to cross into the next split. PR #84 adds a label-window embargo; old metrics must be treated as stale until retraining.
- **Cyclone + rainfall association:** The target is same-day extreme rainfall, not a joint cyclone-flood impact. There is no forecast lead time. The full dataset has only 128 cyclone-near days and about 20 cyclone-near extreme-rain days. Brier (0.1378) is worse than base rate (0.0649), ECE is 0.229, and removing cyclone features changes test PR-AUC by only +0.005. Keep excluded from inference.

## Cross-cutting limitations

1. **No independent validation:** all six cards use one chronological holdout. No independent geographic holdout is reported.
2. **Single-location weather training:** the weather model specifications use Kochi only, even though other location records exist in the repository. Transferability is unknown.
3. **Proxy labels:** rainfall is not flood; Tmax percentile is not an official heatwave; 30-day rainfall deficit is not hydrological drought; aftershock occurrence is not earthquake prediction.
4. **Event scarcity and dependence:** drought has 36 positive test rows; cyclone rapid intensification has 86; compound cyclone-near extreme-rain examples are sparse. Daily weather rows are autocorrelated, while storm and earthquake records require event/sequence-aware splits.
5. **Probability quality differs from ranking:** rainfall, cyclone and compound association have Brier scores worse than their base-rate references. ROC-AUC/PR-AUC alone do not justify probability use.
6. **Feature-name leakage checks are not sufficient:** each feature needs a documented source, timestamp, location and proof it would be available at the intended issue time.
7. **Source quality needs stratified audits:** report missingness by period/location, station/source changes, catalogue completeness, duplicate events, timestamp alignment and revisions.

## Additional data and preferred modelling by hazard

| Hazard | Data required before a defensible model | Preferred primary approach |
| --- | --- | --- |
| Flood | Geolocated inundation extent/depth/duration; river gauges and datum; rain gauges/radar; drainage/pump/outfall records; DEM/catchment connectivity; tide and verified event timelines | Hydrologic/hydraulic modelling and evidence-based flood mapping. ML only for well-labelled rainfall/runoff or rapid mapping tasks. |
| Cyclone | Archived forecast-cycle track/intensity/wind/rainfall with issue/valid times; best-track outcomes; storm/basin IDs; surge and local exposure observations | Numerical weather prediction and ensemble guidance; ML may post-process forecast guidance with independent storm/basin tests. |
| Earthquake | Complete regional catalogue with magnitude-of-completeness metadata; reviewed sequence membership; location/depth uncertainty; ground-motion/site/geology data | Statistical aftershock/point-process models and seismic engineering. Do not claim mainshock prediction. |
| Landslide | Dated geolocated inventory plus defensible background/non-event sampling; slope, geology, soil, land cover, road cuts, drainage and rainfall intensity/duration | Geotechnical susceptibility/stability and rainfall-threshold models; supervised ML only with spatially independent validation. |
| Heatwave | Quality-controlled station Tmax/Tmin, humidity/heat index, night temperature, official IMD criteria, consecutive-day labels and exposure | Weather forecasts plus official-rule verification; ML may post-process temperature forecasts. |
| Drought | Long-term station rainfall, SPI/SPEI, soil moisture, evapotranspiration, groundwater, reservoir/storage, streamflow and demand | Physical/statistical drought indices and water-balance models; ML may support outlooks after multi-year/spatial validation. |
| Industrial incident | Facility process/safety data, release and near-miss records, inspections, sensor/meteorology data, representative non-event operating periods | Process-safety engineering, fault trees and dispersion modelling; ML only with representative positive and negative labels. |
| Infrastructure failure | Asset condition/maintenance, load, outage/failure/restoration times, network topology and service dependencies | Reliability engineering and graph/dependency cascade analysis; ML only with asset-level labelled histories. |
| Cyclone + flood | Synchronized storm forecast/track, rain, river/tide/surge, drainage and geolocated flood impacts from the same events | Coupled physical models and event-aligned scenario analysis; do not add independent scores and call it compound risk. |
| Heavy rainfall + drainage failure | Rainfall intensity/accumulation, drain capacity/condition, pump/outfall operation, waterlogging depth/duration and verified asset failures | Urban drainage/hydraulic modelling and dependency analysis; ML only with verified event labels and controls. |

## Remediation order

### P0 — correct validity defects
- Retrain earthquake after applying the seven-day outcome-window embargo; regenerate its model card and validation report.
- Add and inspect an earthquake sequence/persistence baseline.
- Reassess flood and cyclone against persistence and base-rate references; their current F1 does not beat persistence and Brier is worse than base rate.
- Keep compound cyclone-rainfall excluded from inference.
- Make model cards distinguish target proxy, source type, event count, split dates, geographic coverage and issue-time feature availability.

### P1 — stronger evaluation
- Add rolling-origin temporal backtests.
- Add rotating geographic holdouts for weather models.
- Add storm/basin holdouts for cyclone models and sequence-aware holdouts for earthquakes.
- Use block/event bootstrap intervals that preserve temporal/event dependence.
- Report metrics by season, location, event class and source era, with base-rate and persistence baselines.

### P2 — scientifically appropriate models
- Do not force supervised ML onto hazards without credible labels.
- Keep physical, statistical and evidence-based approaches primary where mechanisms and data demand them.
- Share data contracts, feature-time checks, evaluation, calibration, uncertainty, registry and presentation services; do not create duplicate engines.
- Promote no model until repeatable skill is shown against appropriate baselines on independent temporal and spatial/event holdouts.

## Product boundary

The general Decision Workflow and specialized scenario workspace must use the same shared ML service. The specialized workspace should accept all ten registered hazards and multiple selections. Custom unregistered disasters remain qualitative and must not be assigned a registered model. PR #83 implements the workspace extension; PR #84 addresses the earthquake label-window issue. Both are draft and unverified until CI and local smoke tests pass.
