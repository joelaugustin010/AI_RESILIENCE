# Phase 2 data dictionary

The source files are preserved as acquired; column names and source units are
not silently rewritten. The JSON sidecars and provenance register contain the
complete snapshot metadata and exact hashes.

## NWIC/NWDP CSV snapshots

Common source fields include `Station`, `Agency`, state/district codes,
administrative text fields, `Latitude`, `Longitude`, and
`Data Acquisition Time`. Do not assume station coordinates or timestamp
timezone are authoritative without provider confirmation.

| File | Measurement column | Source-declared unit | Timestamp field | Rows / observed dates |
|---|---|---|---|---|
| `nwdp_cwc_rainfall_2021_2025.csv` | `Telemetry Hourly Rainfall (mm)` | mm per source label | `Data Acquisition Time` | 9,206; 2021-01-03 20:30 to 2025-12-28 02:00 |
| `nwdp_manual_rainfall_1991_2020.csv` | `Manual Hourly Rainfall (mm)` | mm per source label | `Data Acquisition Time` | 109,978; 2000-02-27 21:30 to 2014-12-31 17:30 |
| `nwdp_manual_river_level_2021_2025.csv` | `River Water Level Manual Hourly (meter)` | metres per source label | `Data Acquisition Time` | 16,005; 2022-01-01 08:00 to 2025-03-31 16:00 |
| `nwdp_telemetry_river_level_2021_2025.csv` | `River Water Level Telemetry Hourly (meter)` | metres per source label | `Data Acquisition Time` | 107,064; 2021-06-11 20:00 to 2025-03-10 14:00 |

`SlNo` is a source row number, not a stable observation identifier. CWC's
download has `Block` and `Village`; the pre-existing local copy instead has
`_id`. Duplicate station-time keys are preserved. In particular, do not
silently collapse conflicting CWC rainfall readings.

## IMD NetCDF

| Variable | Dimensions/units | Meaning |
|---|---|---|
| `LONGITUDE` | longitude axis; degrees east | Grid cell longitude coordinates. |
| `LATITUDE` | latitude axis; degrees north | Grid cell latitude coordinates. |
| `TIME` | annual daily axis; `days since 1900-12-31 00:00:00` | Date coordinate. |
| `RAINFALL` | `TIME`, `LATITUDE`, `LONGITUDE`; mm | Daily gridded rainfall. `-999` is the recorded fill value and is treated as missing. |

The processing extracts the nearest cell to 9.93 N, 76.27 E. In the acquired
files it is centered at 10.00 N, 76.25 E. The data source does not explicitly
state a datum/authority CRS; the processor records coordinates in degrees and
does not claim a precise local geometry.

## NASA POWER JSON

Daily values are keyed by `YYYYMMDD`; the response declares UTC and a fill value.
The loader maps that fill value to missing without converting it to zero.

| Parameter | Response unit | Interpretation |
|---|---|---|
| `PRECTOTCORR` | mm/day | Bias-corrected precipitation product. |
| `T2M` | C | Daily mean 2-m air temperature product. |
| `T2M_MAX` | C | Daily maximum 2-m air temperature product. |
| `T2M_MIN` | C | Daily minimum 2-m air temperature product. |
| `WS10M` | m/s | Wind speed product at 10 m. |

These are gridded/model-derived data at a fixed request point, not verified
station values or values geocoded from the user-entered assessment area.

## OSM, USGS, and existing environmental files

- OSM Overpass uses an `elements` array. The Phase 2 summary counts `way`
  elements tagged with `highway`; it does not construct a routable graph.
- USGS response is a GeoJSON `FeatureCollection`. The query result count is
  metadata about that bounded API request, not a seismic-risk indicator.
- Existing JRC GeoTIFFs, KSDMA ZIP, hospital directory, ward geometry, KSPCB
  reports, and industrial consent records are described in
  `data/reference/spatial_sources.json`,
  `data/reference/air_quality_acquisition.json`, and
  `DATA_SOURCES.md`. Their original attributes/CRS/units are not reinterpreted
  by the Phase 2 grid reader.

## Processing output fields

`load_imd_rainfall_cell` returns `date` and `rainfall_mm` and records selected
cell, reference coordinate, cell offset, valid/missing daily count, range,
mean, fill value, time units, and a CRS caveat. `load_nasa_power` returns
`date` and the five NASA parameter columns plus date range, units, fill counts,
and returned coordinate. OSM/USGS readers return source metadata and counts
with explicit non-inference statements.
