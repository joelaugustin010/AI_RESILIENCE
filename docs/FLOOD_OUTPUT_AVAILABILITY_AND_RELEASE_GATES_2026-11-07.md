# Flood output availability and scientific boundaries

Updated 2026-11-07 for PR #82.

## Outputs users can obtain now

- Rainfall amount and mean intensity: calculated from the entered depth and explicit interval. This is not peak intensity or flood probability.
- Rational Method peak runoff: conditional on rainfall duration, catchment area and runoff coefficient. It is a simplified peak-flow estimate, not water depth or inundation.
- Drainage scenario screening: conditional on entered flow/capacity assumptions; not a measured drainage-failure probability.
- Population exposure: available through the existing GeoJSON upload calculator when a complete, non-overlapping population grid and a compatible hazard-footprint polygon layer are supplied. It is approximate population presence, not casualties or displacement.
- Flood extent/depth summary: the new optional GeoJSON tool measures area and area-weighted depth from a supplied polygon depth layer. Each feature must contain a positive `depth_m` (or configured property), and the user must verify event date, CRS, vertical datum, units, coverage and licence. It does not generate a flood map or forecast.

## Outputs intentionally withheld

### Flood occurrence probability

Not available until a local, time-stamped event/non-event record is assembled with compatible rainfall, river/tide, drainage and catchment predictors, then evaluated with temporal/event holdouts and calibrated probability uncertainty. Rainfall exceedance alone is not flood probability.

### Predicted depth and extent

Not available as a forward prediction until a locally configured hydraulic model has terrain, drainage/network geometry, boundary conditions (including river/tide/backwater where relevant), calibrated parameters and independent observed flood marks/extent for validation. A supplied depth-layer summary is descriptive only.

### Damage and casualty prediction

Not available until geocoded buildings/assets, occupancy and vulnerability/fragility functions, time-specific exposure, response context and independently verified damage/casualty labels exist. Population inside a footprint must never be relabelled as injured, displaced or killed.

## Release rule

No new flood probability, hydraulic prediction, damage estimate, casualty estimate, accuracy claim or operational warning is asserted by this update. The new tool is an evidence-ingestion/measurement capability only. All model outputs remain research or scenario support and cannot replace KSDMA/IMD/CWC/local-authority instructions.
