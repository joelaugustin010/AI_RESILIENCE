# Phase 2 data sources

**Snapshot/review date:** 2026-11-01
**Scope:** Public or already-present data relevant to Kochi and Ernakulam. A source
being official, open, or checksum-valid does not by itself establish accuracy,
completeness, fitness for a particular analysis, or permission to redistribute.

## Acquired in this phase

All new downloads are preserved as research-only snapshots under
`data/raw/experimental/`. Their retrieval metadata, quality checks, and SHA-256
hashes are in the adjacent `.metadata.json` files and
`data/reference/DATA_PROVENANCE_REGISTER.json`.

| Dataset | Publisher/source | Coverage and purpose | Use status and principal limitation |
|---|---|---|---|
| CWC telemetry rainfall | Central Water Commission, served by NWIC/NWDP; [resource](https://nwdp.nwic.gov.in/dataset/792f0818-bedf-42ab-a119-dc7002ceb312/resource/654dd5af-ec2c-4439-a8a5-f9bf5d61ab74/download/rainfall_tel_hr_cwc_kl_2021_2025.csv) | 4 stations; 2021-01-03 to 2025-12-28; source-stated hourly rainfall in mm | Experimental; 1,471 duplicate station-time groups and 324 with conflicting values. Station metadata, timing/QC, and resolution for local use need provider review. |
| Kerala manual rainfall | Kerala Surface Water Department, served by NWIC/NWDP; [resource](https://nwdp.nwic.gov.in/dataset/5deb3a6d-2fec-47f1-8a38-637137fb3dbb/resource/ceb9ffcf-927b-4b34-8ab5-6c3098dd95a9/download/rainfall_manual_hr_kerala-sw_kl_1991_2020.csv) | 21 stations; 2000-02-27 to 2014-12-31; source-stated hourly rainfall in mm | Experimental and historical; filename/catalog period says 1991-2020 but observed records cover 2000-2014. Not a current Kochi forecast or outcome label. |
| Kerala manual river level | Kerala Surface Water Department, served by NWIC/NWDP; [resource](https://nwdp.nwic.gov.in/dataset/b7ed6f63-d702-429b-a342-c3e2acd31ad6/resource/fe95a85e-142d-4acf-83fc-24499afc546b/download/rwl_manual_hr_kerala_sw_031_2021_2025.csv) | 6 stations; 2022-01-01 to 2025-03-31; source-stated metres | Experimental; the filename starts in 2021 but the first record is in 2022. Gauge datum/zero and warning thresholds are not resolved. |
| Kerala telemetry river level | Kerala Surface Water Department, served by NWIC/NWDP; [resource](https://nwdp.nwic.gov.in/dataset/1a00209e-c864-4c1c-bc82-b5e2d8ecb66e/resource/a6de190e-40b6-484b-ad4c-a9f811f061ba/download/rwl_tel_hr_kerala_sw_031_2021_2025.csv) | 6 stations; 2021-06-11 to 2025-03-10; source-stated metres | Experimental; gauge datum/zero, telemetry QA, and operational thresholds remain unknown. |
| IMD 0.25-degree daily rainfall | India Meteorological Department, Climate Research and Services, Pune; [product page](https://www.imdpune.gov.in/cmpg/Griddata/Rainfall_25_NetCDF.html) | Annual India-wide NetCDF grids for 2018, 2021, and 2024; rainfall in mm; 0.25-degree grid | Research-only nearest-cell extraction. The product page describes data through 2024 and requests citation of Pai et al. (2014), but an explicit reuse licence was not found. Source datum/authority CRS is not stated. |
| NASA POWER daily point API | NASA Langley Research Center; [acquired API request](https://power.larc.nasa.gov/api/temporal/daily/point?parameters=PRECTOTCORR%2CT2M%2CT2M_MAX%2CT2M_MIN%2CWS10M&community=SB&longitude=76.27&latitude=9.93&start=20200101&end=20250101&format=JSON&time-standard=UTC) | 2020-01-01 through 2025-01-01 inclusive; precipitation, temperature, and 10-m wind at fixed request point 76.27 E, 9.93 N | Context only. Gridded/model-derived, not an in-situ station. No calibration, local flood threshold, or event-impact link. Confirm current data-use terms before redistribution. |
| OSM road ways | OpenStreetMap contributors; [Overpass query](https://overpass-api.de/api/interpreter?data=%5Bout%3Ajson%5D%5Btimeout%3A60%5D%3Bway%5B%22highway%22%5D%289.8934161%2C76.2373589%2C10.0497693%2C76.3400293%29%3Bout+geom%3B) | 16,378 highway-tagged ways within a rectangle based on an existing provisional ward snapshot | Context only; completeness, positional quality, access, condition, and date-specific passability are not verified. ODbL attribution and share-alike requirements may apply. |
| USGS earthquake catalog query | USGS Earthquake Hazards Program; [query](https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&starttime=1900-01-01&endtime=2026-11-01&minlatitude=8&maxlatitude=12&minlongitude=74&maxlongitude=79&minmagnitude=0&orderby=time-asc) | 1900-01-01 through 2026-11-01; 8-12 N, 74-79 E; minimum magnitude 0 | API returned zero records. This does not mean zero seismic hazard or a complete local catalogue; no local building vulnerability is inferred. |

## Existing repository sources retained

These are pre-existing project files and are inventoried, but were not
replaced or reclassified as validated data in this phase.

| Source family | Source and current role | Limitations |
|---|---|---|
| JRC/Copernicus GloFAS RP100 depth | [JRC product README](https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/CEMS-GLOFAS/flood_hazard/README.txt); existing `data/raw/jrc_glofas_*_depth.tif` files | Modelled return-period scenario, not an observation or forecast. Existing project review identifies hazard-tile/preview limits and no verified hospital exposure layer. Transparent/NoData pixels do not imply safety. |
| KSDMA flood archive | Existing `data/raw/ksdma_flood_return_probability_historical_10_25_50.zip` and associated metadata | Pixel semantics, NoData, method, return-period meaning, original source/attribution, and reuse permission are unresolved. The ZIP is not suitable for risk calculation until these questions are answered. |
| Kochi ward/boundary data | DataMeet and Kerala OpenSDI references in `data/reference/spatial_sources.json`; existing provisional boundary and 2022 ward files | Not a current authoritative municipal boundary/ward release. Geometry/CRS and licensing limitations are recorded in the existing source register. Not used to spatially join new grid data. |
| NIHFW hospital directory | [Government Open Data Platform resource](https://www.data.gov.in/resource/national-hospital-directory-geo-code-and-additional-parameters-updated-till-last-month) | Acquired for review but hospital coordinate validity, completeness, service status, and currentness are not established. Not used for flood exposure or routing. |
| KSPCB air evidence | Existing KSPCB AQI summary JSONs and dated reports under `data/raw/air_quality*`; details in `data/reference/air_quality_acquisition.json` | Dated reports are not a complete pollutant series. Station-name inventory has no validated coordinates; the CPCB live API did not yield observations. AQI or proximity does not attribute pollution to an industry. |
| Industrial records | Existing KSPCB/KWA/DIC documents under `data/raw/industrial/` | Permit/consent records do not establish current emissions or source contribution. Some earlier attempted “PDF” files were malformed/identical payloads; they remain inventoried and are not treated as evidence. |

## Investigated but not acquired

- **NASA GPM IMERG:** [official product description](https://gpm.nasa.gov/data/imerg)
  documents multi-satellite precipitation estimates and Early/Late/Final
  products. The relevant archive requires NASA PPS/Earthdata registration. No
  authentication barrier was bypassed; acquire only through an authorized
  account and confirm terms.
- **NOAA IBTrACS:** [official NCEI archive](https://www.ncei.noaa.gov/products/international-best-track-archive)
  documents version 4r01, citations, technical documentation, and a user
  registration request. The inspected all-storm CSV was about 333 MB. It was
  not downloaded; a source-approved regional or period-limited extract is
  preferable for Kochi cyclone-context work.
- **National Center for Seismology (NCS):** [official portal](https://seismo.gov.in/)
  is an Indian government source. A validated, downloadable local catalogue
  with documented completeness, location uncertainty, magnitudes, and reuse
  terms was not acquired in this pass.
- **Geological Survey of India (GSI):** the [Bhukosh portal](https://bhukosh.gsi.gov.in/Bhukosh/Public)
  was identified for geoscience context, but its endpoint failed transport/DNS
  retrieval during this run. No local earthquake hazard layer was downloaded.
- **CWC live gauge data and KSDMA flood layers:** investigated through existing
  NWDP/KSDMA records. The downloaded NWDP files are not enough to resolve
  station identity, gauge datum, operational thresholds, or CWC data conflicts.
- **CPCB/KSPCB pollutant observations and emissions:** official catalogues and
  monitoring pages were inspected. The reviewed public pages did not provide a
  downloadable, well-described Kochi pollutant time series with sampling,
  units, coordinates, quality flags, and reuse terms. Access or permissions
  remain required.
- **Drainage, current hospital/emergency facilities, utilities, population,
  industrial emissions, and authoritative road condition:** no complete,
  current, quality-described Kochi layers with suitable permissions were
  available in the reviewed repository or sources. OSM is not a substitute for
  these datasets.

## Source-selection rule

New sources stay in the experimental area until provenance, licence, coverage,
and question-specific suitability have been reviewed. The workflow never
interprets unavailable data as zero hazard, exposure, or risk. See
`DATA_QUALITY_REPORT.md`, `DATA_GAPS.md`, and `DATA_TO_MODEL_MAPPING.md`.
