# Phase 2 data sources

**Snapshot/review date:** 2026-11-02  
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
| NOAA GHCN-Daily Ernakulam and Fort Cochin | NOAA NCEI; [station inventory](https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd-stations.txt), [Ernakulam](https://www.ncei.noaa.gov/pub/data/ghcn/daily/all/IN010032300.dly), [Fort Cochin](https://www.ncei.noaa.gov/pub/data/ghcn/daily/all/IN010033100.dly) | Daily PRCP source records cover 1901–1970 at the inventory-listed stations; raw values are tenths of mm and M/Q/S flags are retained. | Acquired and structurally validated; dataset-level downstream reuse terms unresolved, not integrated. Historical records do not validate recent flood events. Details/checksums are in `data/raw/ghcn/*.metadata.json`. |
| IMD 0.25-degree daily rainfall | India Meteorological Department, Climate Research and Services, Pune; [product page](https://www.imdpune.gov.in/cmpg/Griddata/Rainfall_25_NetCDF.html) | Annual India-wide NetCDF grids for 2018, 2021, and 2024; rainfall in mm; 0.25-degree grid | Research-only nearest-cell extraction. The product page describes data through 2024 and requests citation of Pai et al. (2014), but an explicit reuse licence was not found. Source datum/authority CRS is not stated. |
| NASA POWER daily point API | NASA Langley Research Center; [acquired API request](https://power.larc.nasa.gov/api/temporal/daily/point?parameters=PRECTOTCORR%2CT2M%2CT2M_MAX%2CT2M_MIN%2CWS10M&community=SB&longitude=76.27&latitude=9.93&start=20200101&end=20250101&format=JSON&time-standard=UTC) | 2020-01-01 through 2025-01-01 inclusive; precipitation, temperature, and 10-m wind at fixed request point 76.27 E, 9.93 N | Context only. Gridded/model-derived, not an in-situ station. No calibration, local flood threshold, or event-impact link. Confirm current data-use terms before redistribution. |
| OSM road ways | OpenStreetMap contributors; [Overpass query](https://overpass-api.de/api/interpreter?data=%5Bout%3Ajson%5D%5Btimeout%3A60%5D%3Bway%5B%22highway%22%5D%289.8934161%2C76.2373589%2C10.0497693%2C76.3400293%29%3Bout+geom%3B) | 16,378 highway-tagged ways within a rectangle based on an existing provisional ward snapshot; processed context includes 1,564 major-road and 347 bridge-tagged ways. | Map context only; completeness, positional quality, access, condition, and date-specific passability are not verified. ODbL attribution and share-alike requirements may apply. No routing or exposure calculation. |
| USGS earthquake catalog query | USGS Earthquake Hazards Program; [query](https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&starttime=1900-01-01&endtime=2026-11-01&minlatitude=8&maxlatitude=12&minlongitude=74&maxlongitude=79&minmagnitude=0&orderby=time-asc) | 1900-01-01 through 2026-11-01; 8-12 N, 74-79 E; minimum magnitude 0 | API returned zero records. This does not mean zero seismic hazard or a complete local catalogue; no local building vulnerability is inferred. |

## Additional original snapshots acquired 2026-11-02

These eight files were downloaded directly from the publishers' public endpoints
and validated as described in
[DATA_ACQUISITION_REPORT.md](DATA_ACQUISITION_REPORT.md). They are preserved
under `data/raw/experimental/kochidata_2026-11-02/`; SHA-256 values are
reproducibly indexed by sidecars and the provenance register.

| Dataset / local snapshot | Publisher and official URL | Coverage / date and licence | Verification / use status |
|---|---|---|---|
| [KSDMA Ernakulam flood map PDF](../data/raw/experimental/kochidata_2026-11-02/ksdma_ernakulam_historical_flood_probability_2022.pdf) | KSDMA; [PDF](https://sdma.kerala.gov.in/wp-content/uploads/2022/05/Ernakulam_Hist.pdf) | Ernakulam district; PDF modified 2022-05-20; Kochi Taluk map pages for 10–500-year return-probability scenarios. Licence not stated. | 58 pages and geospatial viewports inspected; reference-only boundaries; not observed event data and not redistributed/integrated pending permission. SHA-256 `b0420a8e878c0e6205be51f6735bc6e6900254667f11af6d8b4f95f87026d08b`. |
| [KSDMA Kerala flood probability report](../data/raw/experimental/kochidata_2026-11-02/ksdma_flood_probability_report_2022.pdf) | KSDMA/Kerala State Emergency Operations Centre; [report](https://sdma.kerala.gov.in/wp-content/uploads/2022/06/Flood-Probability-Report-2022_Final.pdf) | Kerala districts; 2022; modelled historic/climate-scenario hazard and school/hospital exposure. Licence not stated. | 427-page PDF parsed; not an event-by-event observed impact registry; permission required. SHA-256 `11976ae741ff3e6a306ad67d99a93b2ed1b13577f803b807daa3220d3c3f672e`. |
| [UNEP–KSDMA historical inundation map](../data/raw/experimental/kochidata_2026-11-02/ksdma_unep_historical_flood_inundation_map_2020.pdf) | KSDMA, credited to UNEP–KSDMA (2020); [map](https://sdma.kerala.gov.in/wp-content/uploads/2022/02/Image_Final.pdf) | Historical-based 2020 product; 6 PDF pages; exact event period/municipal coverage not validated. Licence not stated. | PDF structure valid, text not extractable for map semantics; research-only, permission and geospatial interpretation required. SHA-256 `797d00352f3a2e4f5b41c5e71d68ae2b8632ff9cdbe2dbe1338ffe8373d26d04`. |
| [GSI Ernakulam susceptibility archive](../data/raw/experimental/kochidata_2026-11-02/gsi_ernakulam_landslide_susceptibility_2022.zip) | GSI, distributed by KSDMA; [ZIP](https://sdma.kerala.gov.in/wp-content/uploads/2025/08/Ernakulam.zip) | GSI 2022; three polygons, EPSG:32643; observed bounds do not overlap approximate Kochi review bounds. Licence not stated. | ZIP CRC and shapefile structure valid; class meanings/topology not verified; not city coverage and not integrated. SHA-256 `7bac333a4a2c26410582555dbf722157fa97df63fafa24b5a0bb8ef269935b20`. |
| [GSI Kerala district susceptibility PDF](../data/raw/experimental/kochidata_2026-11-02/gsi_kerala_district_landslide_susceptibility_2022.pdf) | GSI/KSDMA; [PDF](https://sdma.kerala.gov.in/wp-content/uploads/2025/06/Landslide_Susceptibility_Zones_Districts_FINAL.pdf) | GSI 2022; 14 pages, includes district maps; licence not stated. | PDF structure/text inspected; boundaries called unverified/reference-only; not spatially integrated. SHA-256 `1b1b712b3bd052e7f93422813fd929750f43bddfc2e0317ed8c30b1fc46a0bd6`. |
| [Copernicus DEM GLO-30 tile](../data/raw/experimental/kochidata_2026-11-02/copernicus_dem_glo30_N09E076.tif) | Copernicus Programme; [tile](https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N09_00_E076_00_DEM/Copernicus_DSM_COG_10_N09_00_E076_00_DEM.tif), [registry](https://registry.opendata.aws/copernicus-dem/) | 2021 DSM; bounds 76.00–77.00 E, 9.00–10.00 N; Copernicus DEM licence. | EPSG:4326, Float32, 3600² pixels; Kochi reference point and 10,000-cell window valid; vertical datum and hydrologic use unresolved. SHA-256 `41e01d500c614d505254f5026693e148c0956b8f0e8aa6cc03bdb81c1fbe204a`. |
| [ESA WorldCover 2021 v200 map tile](../data/raw/experimental/kochidata_2026-11-02/esa_worldcover_10m_2021_v200_N09E075_Map.tif) | ESA WorldCover; [tile](https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_N09E075_Map.tif), [registry](https://registry.opendata.aws/esa-worldcover-vito/) | 2021 classification; bounds 75–78 E, 9–12 N; CC BY 4.0. | EPSG:4326, 10 m class raster; Kochi point covered; sample includes class codes 10, 30, 40, 50, 60, 80. Not buildings or validated imperviousness. SHA-256 `913f22dd9ba2b05f52eeb104ca88aa5162ec2d0a5dcef1124d4f19546ac49558`. A downsampled display-only context preview is available at [worldcover preview](../data/processed/spatial_layers/worldcover_2021_kochi_context.png), SHA-256 `4e1c1ee22da53f0dec86b9a63fbf9d840abb11d1d60ffdf930e34d8ef9d796dd`, with exact processing in its metadata sidecar; no spatial exposure calculation is performed. |
| [WorldPop India 2025 population grid](../data/raw/experimental/kochidata_2026-11-02/worldpop_india_2025_constrained_100m_R2025A_v1.tif) | WorldPop; [summary](https://hub.worldpop.org/geodata/summary?id=24777), [raster](https://data.worldpop.org/GIS/Population/Global_2015_2030/R2025A/2025/IND/v1/100m/constrained/ind_pop_2025_CN_100m_R2025A_v1.tif) | India, modelled 2025, nominal 100 m; dataset-specific licence not established in inspected summary. | EPSG:4326 and Kochi coverage verified; sample window 5,354 valid and 4,646 NoData. Modelled people-per-cell, not census/households; no redistribution or integration before rights and local accuracy confirmation. SHA-256 `f5717c622d79052d4aacf0f67365165575855ba8059375b5d87ea655ed26fa53`. |

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
  registration request. The all-storm CSV was about 333 MB and was not
  downloaded; the North Indian Ocean v4r01 CSV was acquired and structurally
  checked. Since the product page and DOI metadata did not establish
  dataset-level reuse terms, it remains rights-review-only and is not
  integrated or distributed with the app.
- **National Center for Seismology (NCS):** [official portal](https://seismo.gov.in/)
  is an Indian government source. A validated, downloadable local catalogue
  with documented completeness, location uncertainty, magnitudes, and reuse
  terms was not acquired in this pass.
- **Geological Survey of India (GSI):** the [Bhukosh portal](https://bhukosh.gsi.gov.in/Bhukosh/Public)
  was identified for geoscience context, but its endpoint failed transport/DNS
  retrieval during this run. No local earthquake hazard layer was downloaded.
  A separate GSI landslide susceptibility archive was acquired from KSDMA and
  did not spatially overlap the approximate Kochi review bounds.
- **CWC live gauge data and KSDMA flood layers:** investigated through existing
  NWDP/KSDMA records. The downloaded NWDP files are not enough to resolve
  station identity, gauge datum, operational thresholds, or CWC data conflicts.
- **CPCB/KSPCB pollutant observations and emissions:** official catalogues and
  monitoring pages were inspected. The reviewed public pages did not provide a
  downloadable, well-described Kochi pollutant time series with sampling,
  units, coordinates, quality flags, and reuse terms. Access or permissions
  remain required.
- **Drainage, current hospital/emergency facilities, utilities, household
  counts, industrial emissions, and authoritative road condition:** no
  complete, current, quality-described Kochi layers with suitable permissions
  were available. A WorldPop 2025 modelled population raster was acquired,
  but its local accuracy and dataset-specific reuse terms are unresolved;
  it is not census/household data. OSM is not a substitute for authoritative
  asset records.

## Source-selection rule

New sources stay in the experimental area until provenance, licence, coverage,
and question-specific suitability have been reviewed. The workflow never
interprets unavailable data as zero hazard, exposure, or risk. See
`DATA_QUALITY_REPORT.md`, `DATA_GAPS.md`, and `DATA_TO_MODEL_MAPPING.md`.

## Additional official sources checked 2026-11-02

### Census of India 2011 — Ernakulam District Census Handbook

The official Census Digital Library exposes records for
[Part A (catalog 644)](https://censusindia.gov.in/nada/index.php/catalog/644)
and [Part B (catalog 645)](https://censusindia.gov.in/nada/index.php/catalog/645).
Both original PDFs and the associated Kerala-wide village/town directory
workbooks were downloaded to
`data/raw/experimental/kochidata_2026-11-02/`; checksums and detailed
workbook/PDF validation are in their sidecars and the provenance register.
Part A describes village/town facilities and amenities; Part B contains
2011 village/town Primary Census Abstract data. The workbooks have Kerala-wide
coverage and include Ernakulam records, but no geospatial boundaries or CRS.
These are historical administrative statistics, not current household
counts, facility inventories, or exposure layers. No explicit reuse licence
was found on the catalog records, so they remain research-only pending rights
confirmation.

### Kerala Land Resources Information System (LRIS 2.0)

The official [LRIS 2.0 application](https://lris.kslub.kerala.gov.in/app/)
advertises Ernakulam `drains`, `roads`, `waterbodies`, and `watersheds` layers
through its public WMS at
`https://gis.duk.ac.in/wlris/LRIS_shp/wms`. The advertised EPSG:4326 extents
intersect the approximate Kochi-area review bounds. The public WMS
GetCapabilities response was inspected; WFS explicitly returns
`ServiceUnavailable` because WFS is disabled. A map portrayal is not a
downloadable validated feature dataset. Dataset dates, feature schema,
accuracy, completeness, drainage capacity, and reuse terms were not
available, so no LRIS features were acquired or integrated.

Other sources investigated for this follow-up did not yield an additional
public, validated Kochi event-impact or drainage/utility data file. This
includes the KSDMA report page (which links modeled/return-period products,
not observed event footprints) and public LRIS services (WMS-only). See the
updated acquisition and data-quality reports for exact remaining blockers.
