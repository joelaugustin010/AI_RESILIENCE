# Reproducing the derived evidence reports

Two committed reports are produced by offline, read-only builder scripts. The
Streamlit app reads the committed JSON; it never runs these builders during a
request. Rebuild them only when the documented inputs change.

## 1. JRC RP100 x OSM provisional exposure screening

Output: `reports/jrc_rp100_osm_exposure_screening.json`

Inputs (tracked in this repository):

- `data/raw/jrc_glofas_rp100_ID185_N20_E70_depth.tif`
- `data/raw/jrc_glofas_rp100_ID186_N10_E70_depth.tif`
- `data/raw/ID185_N20_E70_permanent_water.tif`
- `data/raw/ID186_N10_E70_permanent_water.tif`
- The five provisional OSM GeoJSON layers under
  `data/processed/spatial_layers/osm_kochi_*`
- `data/processed/spatial_layers/jrc_glofas_rp100_kochi_preview.metadata.json`
  (for the display bounds)

Command:

```powershell
python scripts/build_exposure_screening.py
```

Expected printed summary (current inputs):

```text
Assets screened: 14,663; in coverage: 941; positive modelled depth: 724
```

The report is provisional screening only. It is not an observed flood
exposure estimate, a damage estimate, or a safe/unsafe classification. See
`data/raw/JRC_GLOFAS_LICENCE.md` for the ODbL 1.0 / CC BY 4.0 attribution and
share-alike requirements.

## 2. Descriptive Kochi climate benchmarks

Output: `reports/kochi_climate_benchmarks.json`

Inputs (kept local; not committed):

- `data/external/hazards/raw/weather/kochi_daily_weather_1991_2025.json`
- `data/external/hazards/raw/weather/kochi_daily_weather_1991_2025.metadata.json`
- `data/external/hazards/raw/weather/kochi_daily_weather_2000_2025.json`
  (overlap comparison only; the records are never spliced)
- `reports/weather_hazard_training.json` (pooled-threshold cross-check only)

Command:

```powershell
python scripts/build_climate_benchmarks.py
```

Expected printed summary (current inputs):

```text
Record: 1991-01-01 to 2025-12-31 (35 complete years)
SPI readiness: READY (35 years)
```

The builder uses the standard library plus `scipy` (already in
`requirements.txt`) for the descriptive SPI-1 series. The app itself only reads
the committed report and does not need the local weather snapshot.

The report stores repository-relative paths only, so it is portable across
checkout locations and does not embed a developer's filesystem path. If the
input is outside the repository, the builder records only its file name.

## Verification

```powershell
python -B -m pytest -q -ra --strict-markers -p no:cacheprovider
```

Both builders are deterministic apart from the `generated_at_utc` timestamp.
