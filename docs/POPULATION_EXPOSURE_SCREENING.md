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


## Raster preparation pipeline

A reproducible raster-to-grid preparation command is now available:

```powershell
python scripts\prepare_population_grid.py `
  --raster data\external\population\ghsl_2025_100m.tif `
  --boundary data\reference\kochi_official_boundary.geojson `
  --boundary-crs EPSG:4326 `
  --output data\processed\population\kochi_population_2025.geojson `
  --population-year 2025 `
  --source-url "https://human-settlement.emergency.copernicus.eu/download.php?ds=pop" `
  --source-title "GHSL residential population grid, 2025" `
  --source-license "CC BY 4.0"
```

The script clips a single-band population-count GeoTIFF to a supplied boundary,
prorates boundary-edge cells by equal-area intersection, preserves NoData gaps,
and writes a GeoJSON FeatureCollection plus a provenance/coverage sidecar.
It refuses missing CRS, invalid boundaries, negative counts, non-finite raster
values, unsupported multi-band inputs, and excessive feature counts. The
boundary CRS must be explicitly supplied. Review the raster's own band
semantics, epoch, scale/offset, resolution and licence before running it.

## Candidate public sources for Kochi

- **GHSL GHS-POP (European Commission JRC):** public residential population
  grids from 1975–2030, with 100 m and 1 km products. The 2025 epoch is a
  modelled/disaggregated estimate, not a new census. GHSL reuse is permitted
  with acknowledgement; the open-data catalogue describes CC BY 4.0.
  Sources: https://human-settlement.emergency.copernicus.eu/datasets.php
  and https://registry.opendata.aws/ghs-pop/
- **WorldPop Global2:** country grids at approximately 100 m and 1 km for
  2015–2030. The India 2028 R2025A product page explicitly labels that release
  alpha; do not silently substitute it for a 2025 reference year. Confirm the
  exact year-specific file and release statement before ingestion:
  https://hub.worldpop.org/project/categories?id=3
- **Census of India 2011 Population Finder/PCA:** official ward/town-level
  counts can be used as an independent historical aggregate check, not as a
  current population grid:
  https://censusindia.gov.in/census.website/en/data/population-finder

For an initial Kochi research baseline, use a documented 2025 GHSL raster
candidate and compare its aggregate against the closest geographically
matching official Census 2011 town/ward totals. A mismatch is a review signal,
not a reason to rescale the grid automatically. The official current Kochi
boundary and ward polygons must be independently reconciled before claiming
ward-level estimates. Do not label 2011 counts or 2025 modelled grids as live
2026 population counts.
