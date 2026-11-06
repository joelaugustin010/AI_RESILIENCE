# Population exposure screening

The Decision Workflow now includes an optional population-exposure calculator. It accepts two user-supplied GeoJSON FeatureCollections:

1. A population grid with polygon cells and a non-negative numeric `population` property. A unique `grid_id` is recommended.
2. A hazard footprint with valid Polygon or MultiPolygon features.

Both files must be in EPSG:4326. The calculator projects them to EPSG:6933 (global equal-area) for intersection, prorates each population cell by the intersected area, and can aggregate results by a source-provided `ward_name` property. It rejects invalid geometries, non-finite/negative counts, duplicate grid IDs, overlapping population cells and unsupported CRS declarations. A spatial index is used for the overlap check.

## In-app use

Open Decision Workflow, submit a scenario, expand **Population exposure calculator**, upload the two GeoJSON files, enter the population reference year and HTTPS source URLs, and confirm that source attribution, reuse terms, CRS, date and coverage have been reviewed.

Expected properties:
- Population grid: `population`, optional `grid_id`, optional `ward_name`.
- Hazard footprint: valid polygon geometry.

## Interpretation

The output is an approximate count of residents represented by the population grid inside the supplied footprint. It assumes population is uniformly distributed within each grid cell. It is not a forecast, casualty estimate, displacement estimate, count of people actually affected, or proof that a location is unsafe.

A numeric result is labelled `SCREENING_ESTIMATE_NOT_VALIDATED`; the code never marks it as validated exposure. The uploaded source URLs and population reference year are retained with the session result. The app does not independently verify the remote source, licence, CRS declaration or publication date; the in-app confirmation is a user attestation, not an automated provenance audit.

## Current Kochi data limitation

No validated Kochi population-grid file or fully authoritative current ward polygon layer is bundled as a ready-to-use exposure input. The 2022 community ward subset has 74 valid polygons, missing attributes and is explicitly not suitable for exposure calculations. Therefore this feature is implemented as an upload-driven calculation path; it does not invent current Kochi population totals or ward-level figures.

## Next validation work

Before presenting an operational estimate, acquire a properly licensed population grid and validated hazard footprint, confirm their dates, CRS, resolution and coverage, inspect cell overlap and missingness, compare aggregate population against an authoritative census/statistical total, and have the spatial methodology reviewed. Hazard-specific footprints need independent model validation and uncertainty estimates.
