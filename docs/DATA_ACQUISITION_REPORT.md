# Phase 2 data acquisition report

**Acquisition dates:** 2026-11-01 and 2026-11-02
**Acquisition code:** `scripts/acquire_phase2_data.py`; `scripts/acquire_kochidata_foundation.py`; `scripts/acquire_census_kochidata.py`; `scripts/validate_ibtracs_north_indian.py`
**Rebuild inventory:** `.venv\Scripts\python.exe scripts\acquire_phase2_data.py inventory`

## Downloaded and inspected

Eight datasets (ten annual/resource files) were downloaded into
`data/raw/experimental/`. None was staged or committed. Their exact byte sizes, SHA-256 values, source URLs,
retrieval times, licence notes, and dataset-specific metadata are recorded in
`data/reference/DATA_PROVENANCE_REGISTER.json` and adjacent JSON sidecars.

| Snapshot(s) | Files | Observed content |
|---|---:|---|
| NWIC/NWDP CWC telemetry rainfall | 1 | CSV; 9,206 rows, 20 fields, 4 stations, 2021-01-03 20:30 to 2025-12-28 02:00; 1,471 duplicate station/time groups and 324 conflicting groups. |
| NWIC/NWDP manual rainfall | 1 | CSV; 109,978 rows, 20 fields, 21 stations, 2000-02-27 21:30 to 2014-12-31 17:30. |
| NWIC/NWDP manual river level | 1 | CSV; 16,005 rows, 23 fields, 6 stations, 2022-01-01 08:00 to 2025-03-31 16:00. |
| NWIC/NWDP telemetry river level | 1 | CSV; 107,064 rows, 23 fields, 6 stations, 2021-06-11 20:00 to 2025-03-10 14:00. |
| IMD 0.25-degree daily rainfall | 3 | NetCDF classic, nationwide 135 x 129 longitude/latitude grid, 365/365/366 days for 2018/2021/2024; daily rainfall in mm. Each file is about 25.4 MB. |
| NASA POWER | 1 | JSON daily series, five parameters, 1,828 dates inclusive from 2020-01-01 through 2025-01-01. |
| OpenStreetMap | 1 | Overpass JSON, 16,378 highway-tagged ways; observed OSM base timestamp 2026-11-01T18:27:21Z. |
| USGS earthquake query | 1 | GeoJSON FeatureCollection, HTTP 200, zero returned features for the documented query. |

The provenance inventory includes previously present assets as well as these
snapshots; it is not a count of the datasets listed in this report alone. The
current regenerated register contains 90 data assets, including the newly
inventoried `.txt` and `.dly` GHCN originals. Sidecars are referenced but are
not counted as data assets.

## Continued acquisition across the five priority categories (2026-11-02)

Eight additional original files were downloaded and structurally inspected.
All remain in `data/raw/experimental/`; none is an application input. SHA-256,
publisher, source URL, retrieved time, declared terms, and QA details are in
the adjacent sidecars. The complete asset index is regenerated with the
inventory command above.

| Dataset and local original | Publisher / source URL | Date and observed geographic coverage | Licence / rights | SHA-256 and validation |
|---|---|---|---|---|
| KSDMA Ernakulam historical flood probability map, [PDF](../data/raw/experimental/kochidata_2026-11-02/ksdma_ernakulam_historical_flood_probability_2022.pdf) (25,867,743 bytes) | KSDMA; [official PDF](https://sdma.kerala.gov.in/wp-content/uploads/2022/05/Ernakulam_Hist.pdf) | PDF metadata modified 2022-05-20; 58 pages. Six Kochi Taluk map pages cover return periods 10, 25, 50, 100, 200 and 500 years. This is a return-probability map, not dated observed events. | Dataset-specific reuse permission not found; no public redistribution or deployment pending KSDMA permission. | `b0420a8e878c0e6205be51f6735bc6e6900254667f11af6d8b4f95f87026d08b`; PDF structure and geospatial viewports inspected. Map states boundaries are unverified and for reference only. |
| KSDMA Kerala flood probability report 2022, [PDF](../data/raw/experimental/kochidata_2026-11-02/ksdma_flood_probability_report_2022.pdf) (21,992,376 bytes) | KSDMA / Kerala State Emergency Operations Centre; [official report](https://sdma.kerala.gov.in/wp-content/uploads/2022/06/Flood-Probability-Report-2022_Final.pdf) | 2022 report, 427 pages; Kerala districts, with flood-hazard-probability and school/hospital exposure analysis. The methods include modelled historical and climate-scenario products; not an event-by-event observed impact registry. | Dataset-specific reuse permission not found; obtain KSDMA permission before redistribution. | `11976ae741ff3e6a306ad67d99a93b2ed1b13577f803b807daa3220d3c3f672e`; PDF parsed, 427 pages. |
| UNEP–KSDMA historical inundation map 2020, [PDF](../data/raw/experimental/kochidata_2026-11-02/ksdma_unep_historical_flood_inundation_map_2020.pdf) (2,238,906 bytes) | KSDMA page credits UNEP–KSDMA (2020); [official map](https://sdma.kerala.gov.in/wp-content/uploads/2022/02/Image_Final.pdf) | 2020 product, 6 pages; geographic extent and event/time semantics could not be established from extracted text. | Dataset-specific reuse permission not found; obtain KSDMA permission. | `797d00352f3a2e4f5b41c5e71d68ae2b8632ff9cdbe2dbe1338ffe8373d26d04`; PDF structure parsed, but map content is not machine-readable in the inspected text. |
| GSI Ernakulam landslide susceptibility, [ZIP/Shapefile](../data/raw/experimental/kochidata_2026-11-02/gsi_ernakulam_landslide_susceptibility_2022.zip) (3,541,467 bytes) | GSI, distributed by KSDMA; [official archive](https://sdma.kerala.gov.in/wp-content/uploads/2025/08/Ernakulam.zip) | GSI 2022; three polygon features. CRS EPSG:32643; transformed bounds 76.4091064–76.9214579 E, 9.8345281–10.3027237 N. Does not intersect the approximate Kochi review bounds 76.2–76.4 E, 9.8–10.2 N. | No dataset-specific reuse terms found; obtain permission. | `7bac333a4a2c26410582555dbf722157fa97df63fafa24b5a0bb8ef269935b20`; ZIP CRC and shapefile sidecars pass, coordinates finite; polygon topology and class meanings not validated. |
| GSI Kerala district landslide susceptibility map, [PDF](../data/raw/experimental/kochidata_2026-11-02/gsi_kerala_district_landslide_susceptibility_2022.pdf) (9,068,167 bytes) | GSI / KSDMA; [official map PDF](https://sdma.kerala.gov.in/wp-content/uploads/2025/06/Landslide_Susceptibility_Zones_Districts_FINAL.pdf) | GSI 2022; 14 pages, includes Ernakulam district reference map. Boundaries are labelled unverified/reference-only; not a georeferenced city-scale vector. | No dataset-specific reuse terms found; obtain permission. | `1b1b712b3bd052e7f93422813fd929750f43bddfc2e0317ed8c30b1fc46a0bd6`; PDF structure and text inspected. |
| Copernicus DEM GLO-30 Public N09E076, [GeoTIFF](../data/raw/experimental/kochidata_2026-11-02/copernicus_dem_glo30_N09E076.tif) (34,254,776 bytes) | Copernicus Programme; [tile](https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N09_00_E076_00_DEM/Copernicus_DSM_COG_10_N09_00_E076_00_DEM.tif), [registry](https://registry.opendata.aws/copernicus-dem/) | 2021 release; bounds 75.9998611–76.9998611 E, 9.0001389–10.0001389 N, contains the 76.27 E, 9.93 N reference point. 3600×3600, EPSG:4326, Float32. | Copernicus DEM licence; [terms](https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM). | `41e01d500c614d505254f5026693e148c0956b8f0e8aa6cc03bdb81c1fbe204a`; raster metadata and 10,000-cell reference-point window inspected. Vertical reference and bare-earth suitability unresolved. |
| ESA WorldCover 2021 v200, [GeoTIFF](../data/raw/experimental/kochidata_2026-11-02/esa_worldcover_10m_2021_v200_N09E075_Map.tif) (75,590,338 bytes) | ESA WorldCover; [tile](https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_N09E075_Map.tif), [registry](https://registry.opendata.aws/esa-worldcover-vito/) | 2021 classification, v200 released 2022; bounds 75–78 E, 9–12 N, contains the project reference point. 36,000×36,000, EPSG:4326, UInt8. | CC BY 4.0; attribution required. | `913f22dd9ba2b05f52eeb104ca88aa5162ec2d0a5dcef1124d4f19546ac49558`; raster metadata and 10,000-cell reference-point window inspected; six class codes present, no NoData in that window. Not an imperviousness or building layer. |
| WorldPop India 2025 constrained population, [GeoTIFF](../data/raw/experimental/kochidata_2026-11-02/worldpop_india_2025_constrained_100m_R2025A_v1.tif) (778,106,191 bytes) | WorldPop; [dataset summary](https://hub.worldpop.org/geodata/summary?id=24777), [official file](https://data.worldpop.org/GIS/Population/Global_2015_2030/R2025A/2025/IND/v1/100m/constrained/ind_pop_2025_CN_100m_R2025A_v1.tif) | R2025A modelled 2025 estimate; India raster, observed bounds 68.1958323–97.3958322 E, 6.7558336–35.5116669 N, contains Kochi. EPSG:4326, 3-arc-second / nominal 100 m cells; values are estimated persons per cell, not households. | The dataset summary inspected did not establish dataset-specific reuse terms; WorldPop permission/licence confirmation required before redistribution or integration. | `f5717c622d79052d4aacf0f67365165575855ba8059375b5d87ea655ed26fa53`; raster metadata and a 100×100 local window inspected: 5,354 valid cells, 4,646 NoData, values 0–121.1463. NoData is not zero population. |

### Results by requested category

- **1. Flood/hydrology:** acquired three KSDMA flood PDFs with Kochi Taluk
  return-probability maps and report context. Existing CWC/NWDP rain and river
  observations remain the only downloaded local time series. No new observed
  flood event footprint/depth/duration, station metadata, drainage network,
  outfalls, or capacity records were found/acquired.
- **2. Population/land use/terrain:** acquired the WorldPop 2025 modeled India
  population grid, ESA 2021 land-cover tile, and Copernicus GLO-30 surface
  model. They cover the reference point but have material model, time,
  vertical-reference, licensing, or resolution limits. No households,
  surveyed bare-earth DEM, or soil/infiltration layer was acquired.
- **3. Critical infrastructure:** no new authoritative hospital, school,
  road, bridge, utility, or emergency-facility GIS was acquired. Two OSM
  derivatives (1,564 major-road and 347 bridge-tagged ways) are integrated
  only as attributed map context; they do not establish completeness, routing,
  exposure, or disruption. Existing NIHFW limitations remain as documented
  in the source register.
- **4. Historical consequences:** no independent event-by-location impact,
  loss, outage, damage, or service-restoration registry was acquired. KSDMA
  return-probability/exposure PDFs are modeled/reference products, not
  independent event outcomes.
- **5. Environment/industry/economy:** no new pollutant time series,
  facility-specific emissions, industrial release, or economic-loss data was
  acquired. Existing KSPCB/AQI and industrial consent records remain
  context-only and do not support source attribution or losses.

**Application integration:** no newly acquired source files were used as
model inputs. The OSM road and bridge derivatives are wired only as
attributed map context; the GHCN records remain locally retained research
files pending reuse review and are not application inputs. PDFs with
unresolved reuse terms, city coverage gaps, modelled layers, and non-survey
terrain are not promoted to application evidence. This acquisition is useful
progress, but the verified-data foundation is not complete.

## Integrity and pre-existing copy comparison

- The four NWDP payloads match the MD5 values published in their NWDP resource
  metadata. This confirms byte agreement with the portal's published hashes,
  not measurement truth or suitability.
- The three IMD files and NASA/OSM/USGS payloads have local SHA-256 values in
  their sidecars. Readers verify these before parsing.
- The three pre-existing manual rainfall/river CSVs are record-for-record
  equal to the downloaded NWDP payloads after CSV parsing. Their raw byte
  differences are CRLF versus LF line endings.
- The CWC telemetry rainfall copy has the same 9,206 rows and exact shared
  field values after parsing, but its schema differs: the existing file has
  `_id`, while the source snapshot has `Block` and `Village`. The CWC source
  payload also contains 324 conflicting station/time groups. Both files are
  preserved; no rows were discarded or averaged.
- Hash agreement does not imply correctness, licence clarity, completeness, or
  validated station coordinates.

## Processing and validation

`src/phase2_data.py` verifies snapshot hashes, parses NASA POWER JSON, extracts
the nearest IMD grid cell to the fixed 9.93 N, 76.27 E reference point, and
loads OSM/USGS summaries without asserting exposure or hazard. IMD axis/time
checks reject malformed, non-daily, non-finite, wrong-year, or negative
non-fill observations. The processing is descriptive; no risk score, warning,
prediction, or probability is computed.

The selected IMD cell is centered at 10.00 N, 76.25 E, offset by about 0.07
degrees north and 0.02 degrees west from the API/reference point. The extracted
cell has 365, 365, and 366 valid daily values for 2018, 2021, and 2024,
respectively, with no missing cell-days in those three annual files. The
nearest-cell choice is a spatial approximation, not a station or ward join.

At that cell the descriptive annual maximum daily rainfall values are 156.03
mm/day (2018-08-16), 134.57 mm/day (2021-05-15), and 126.21 mm/day
(2024-05-24). These are grid-cell values, not verified gauge measurements,
flood impacts, return periods, or predictions. The annual sum of daily grid
values is not used as a decision score.

NASA POWER reports no fill values in the five selected parameters for this
request. Its date coverage includes the end date 2025-01-01. No station match
or event-specific accuracy evaluation was performed.

## Access limitations and non-downloads

- GPM IMERG relevant downloads require NASA PPS/Earthdata registration. No
  credentials were available or bypassed.
- The inspected global NOAA IBTrACS CSV was approximately 333 MB and was not
  acquired. The North Indian Ocean basin file was acquired separately, but
  remains rights-review-only and is not integrated.
- Public CPCB/KSPCB catalogue pages did not supply a usable and documented
  local pollutant observation extract in this acquisition pass. API-key/
  provider data access and reuse terms remain unresolved.
- There is no validated Kochi drainage or utility network, current hospital
  coordinate layer, local population grid, or facility-specific emission
  inventory among the acquired files.
- The existing KSDMA ZIP and JRC tiles are inventoried as pre-existing project
  data; they were not re-downloaded or promoted to model inputs.

## NOAA GHCN-Daily Kochi-area station acquisition (2026-11-02)

The official NCEI station inventory and two original station `.dly` files
were retrieved from the [GHCN-Daily archive](https://www.ncei.noaa.gov/pub/data/ghcn/daily/).
The sidecars record retrieval at 2026-11-01 21:42 UTC (2026-11-02 local).
The inventory identifies `IN010032300` (ERNAKULAM; 9.9800 N, 76.2800 E,
3 m) and `IN010033100` (FORT COCHIN; 9.9670 N, 76.2330 E, 3 m). The source
inventory is global; only these two stations are relevant to this acquisition.

| Local original | Source URL | Actual observed period and data checks | Licence / status | SHA-256 |
|---|---|---|---|---|
| [`ghcnd-stations.txt`](../data/raw/ghcn/ghcnd-stations.txt) | `https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd-stations.txt` | Global fixed-width station inventory; selected Kochi-area metadata parsed and coordinate ranges checked. | Public download; no explicit downstream dataset licence identified. Retained locally; not distributed with the app. | `437ee87f0343bcad408a492cf7a02163fb69255364c541b4006d5d76055d0dc3` |
| [`IN010032300.dly`](../data/raw/ghcn/IN010032300.dly) | `https://www.ncei.noaa.gov/pub/data/ghcn/daily/all/IN010032300.dly` | PRCP records 1901–1970; 24,865 non-missing values, 493 missing day-values, 3 nonblank quality flags; raw unit is 0.1 mm, source flag `I`. | Same unresolved reuse status; research-only, not integrated. | `cb2214645db614ff4b35a8bfbbfca54308fe19f04afa3e738d469a13f7f2d5eb` |
| [`IN010033100.dly`](../data/raw/ghcn/IN010033100.dly) | `https://www.ncei.noaa.gov/pub/data/ghcn/daily/all/IN010033100.dly` | PRCP records 1901–1970; 25,385 non-missing values, 655 missing day-values, 3 nonblank quality flags; raw unit is 0.1 mm, source flag `I`. | Same unresolved reuse status; research-only, not integrated. | `66d4dea8bbaba2d6a5067569f14a711900a5e1de084dbf1eb67181ed8fb6d5ed` |

The downloader verifies station identity, fixed-width record length, duplicate
year/month/element keys, dates, PRCP values, missing-value sentinels, and
measurement/quality/source flags. Original bytes and flag values are retained.
The source documentation notes that Indian international precipitation series
generally end in 1970; the downloaded records confirm this for both stations.
These are historical point observations, not current rainfall forcing, event
footprints, flood observations, or consequence labels, and cannot validate
recent Kochi floods. Rights remain unresolved, so they are not application
inputs. Per-file provenance, validation summaries and checksums are recorded
in the adjacent metadata sidecars.

Incremental GHCN counts: **discovered 3; downloaded 3; structurally validated
3; integrated 0; partially verified 3; unavailable/requiring permission 3
for application redistribution**. The first six counts describe the three
acquired source files; “partially verified” reflects unresolved downstream
reuse terms and the historical data's limited relevance to current events.

## Reproducibility and preservation

`scripts/acquire_phase2_data.py` performs public requests for Phase 2 sources;
`scripts/acquire_kochidata_foundation.py` acquires and validates the first
eight 2026-11-02 files; `scripts/acquire_census_kochidata.py` acquires and
validates the four Census sources in the follow-up section. Both new
acquisition scripts refuse to overwrite existing originals, check download
lengths, calculate SHA-256, validate file structure/coverage, and maintain
metadata sidecars. Neither authenticates or bypasses access restrictions.
Regenerate the provenance inventory without network requests with
`.venv\Scripts\python.exe scripts\acquire_phase2_data.py inventory`. The
inventory includes `.txt` and `.dly` source files and assigns the GHCN files a
rights-unresolved, not-integrated status.

## Follow-up acquisition: Census and Kerala LRIS (2026-11-02)

This follow-up did not repeat or redownload the prior eight-file acquisition.
It added four unique official Census source files and verified four public LRIS
WMS layer advertisements. The Census files are original downloads from the
Census Digital Library. All remain in the experimental folder and are not
application inputs.

| Dataset / local original | Publisher and official source | Publication and observed coverage | CRS / units | Licence | SHA-256 and actual validation |
|---|---|---|---|---|---|
| [Ernakulam DCHB Part A PDF](../data/raw/experimental/kochidata_2026-11-02/census_2011_ernakulam_dchb_part_a.pdf), 8,390,952 bytes | Office of the Registrar General & Census Commissioner, India / Directorate of Census Operations, Kerala; [catalog 644](https://censusindia.gov.in/nada/index.php/catalog/644) | Census of India 2011; catalog publication 2014; district handbook for Ernakulam; PDF metadata reports 2016 creation/modification. | No spatial CRS; counts and directory attributes defined in source publication. | No explicit reuse licence found on catalog record; redistribution permission remains unresolved. | `9a011544c3e6a9744ad8b8cf941be2275fdcd946e1aa083a3297d2241301af59`; strict PDF parse succeeded, 280 pages, extracted text contains Ernakulam. |
| [Ernakulam DCHB Part B PDF](../data/raw/experimental/kochidata_2026-11-02/census_2011_ernakulam_dchb_part_b.pdf), 5,772,570 bytes | Census Digital Library; [catalog 645](https://censusindia.gov.in/nada/index.php/catalog/645) | Census of India 2011; catalog publication 2014; district village/town Primary Census Abstract. | No spatial CRS; population and household counts. | No explicit reuse licence found on catalog record; redistribution permission remains unresolved. | `ab7a09e1e4ba1f040e3d29546692fe9be5d3392594b4c30691a7000e371ba5f8`; strict PDF parse succeeded, 516 pages, extracted text contains Ernakulam. |
| [Kerala town directory workbook](../data/raw/experimental/kochidata_2026-11-02/census_2011_kerala_town_directory.xlsx), 1,177,278 bytes | Census Digital Library; [catalog 644](https://censusindia.gov.in/nada/index.php/catalog/644), Town Release 3200 | Census 2011; statewide town tables. Three sheets; the `Town_3200` sheet has 524 data rows plus header and 65 rows containing the Ernakulam district name. | No spatial CRS; administrative codes, household/population counts, and service attributes. | No explicit reuse licence found on catalog record; redistribution permission remains unresolved. | `77929074316d0a65c0c6178b9e582c6ab052e1f5552dbd312c82c1fe7c1d7ab4`; ZIP CRC and workbook parse succeeded; three sheets inspected. |
| [Kerala village directory workbook](../data/raw/experimental/kochidata_2026-11-02/census_2011_kerala_village_directory.xlsx), 1,903,185 bytes | Census Digital Library; [catalog 644](https://censusindia.gov.in/nada/index.php/catalog/644), Village Release 3200 | Census 2011; statewide village tables. Three sheets; the `Village_Data_3200` sheet has 1,018 data rows plus header and 69 rows containing the Ernakulam district name. | No spatial CRS; administrative codes, village directory and amenity attributes. | No explicit reuse licence found on catalog record; redistribution permission remains unresolved. | `a46cb9a4760ac0e8167c82d97717738e77cccf4b68434d8cfb2029eea0e9582b`; ZIP CRC and workbook parse succeeded; three sheets inspected. |

The village workbook contains an unparseable header/footer that openpyxl
ignored; its worksheets, cell values, and table headers were read. The parser
warning is preserved in that file's metadata sidecar.

The town workbook contains separately coded town/urban-extension records with
names such as `Kochi (M Corp. + OG) (Part)` and `Kochi (M Corp.) (Part)` in
multiple subdistricts. Those entries must not be summed or spatially joined
without an official boundary/aggregation crosswalk. The files provide
historical administrative reference information only—not current population,
buildings, hospital/school coordinates, or event exposure.

### LRIS layers discovered, but raw data not obtainable through the public service

The Government of Kerala Land Use Department's
[LRIS 2.0 application](https://lris.kslub.kerala.gov.in/app/) advertises the
following Ernakulam layers in the public WMS capabilities document:

| Layer | Advertised CRS / geographic extent | Access result |
|---|---|---|
| `LRIS_shp:drains_ernakulam` | EPSG:4326; 76.1637–76.9193 E, 9.7901–10.3034 N | WMS portrayal advertised; WFS `GetCapabilities` explicitly reports `ServiceUnavailable` / “WFS is disabled.” No raw features, capacity/condition attributes, date, schema or reuse terms obtained. |
| `LRIS_shp:roads_ernakulam` | EPSG:4326; 76.1661–76.8986 E, 9.7901–10.2949 N | WMS-only; no raw feature export or quality/reuse metadata obtained. |
| `LRIS_shp:waterbodies_ernakulam` | EPSG:4326; 76.1600–76.9231 E, 9.7878–10.3060 N | WMS-only; raw geometry and feature definitions unavailable. |
| `LRIS_shp:watersheds_ernakulam` | EPSG:4326; 76.1600–76.9231 E, 9.7872–10.3060 N | WMS-only; watershed hierarchy/method and raw geometry unavailable. |

These extents overlap the approximate Kochi-area review bounds, but are not
municipal-boundary or completeness validation. A rendered map is not a
downloaded analytical layer. The service offers no verified drainage
capacity, outfall, condition, maintenance, connectivity, or stormwater
infrastructure evidence; no LRIS layer was integrated. Details are in
`data/reference/spatial_sources.json`.

### Follow-up counts and unresolved priorities

Counts below describe this follow-up acquisition, not the previously reported
eight-file download:

- **Discovered:** 8 distinct items (4 Census files and 4 LRIS advertised
  service layers).
- **Downloaded:** 4 original Census files.
- **Structurally validated:** 4 downloaded files; no LRIS source features
  were obtained to validate.
- **Integrated:** 0.
- **Partially verified:** 8 items (Census provenance/structure is verified
  but licensing, currency, and spatial fitness are unresolved; LRIS layer
  names, advertised CRS/extents, and WMS-only access are verified, but not
  feature content or suitability).
- **Unavailable for the requested analyses:** 5 remaining dataset groups:
  dated observed Kochi flood footprints/depth/duration; downloadable
  capacity-bearing drainage/outfall data; current local household/building
  layers; current owner-verified facility/utility layers; and event-linked
  consequence records plus verified industrial/emissions/economic exposure.

No observations were inferred from return-period maps or WMS layer names.
Continue to seek owner-approved original extracts and explicit reuse terms;
the newly acquired Census workbooks do not close current spatial-exposure or
historical-validation gaps.

## WorldCover visual context integration (2026-11-02)

The previously acquired ESA WorldCover 2021 v200 tile is now processed into
`data/processed/spatial_layers/worldcover_2021_kochi_context.png` by
`scripts/build_worldcover_kochi_context.py`. The script verifies the original
75,590,338-byte GeoTIFF against SHA-256
`913f22dd9ba2b05f52eeb104ca88aa5162ec2d0a5dcef1124d4f19546ac49558`, reads
only the fixed EPSG:4326 review rectangle 76.15–76.42 E, 9.78–10.12 N, and
creates a downsampled RGBA class-color preview with an accompanying derivative
metadata/checksum sidecar. Preview size is 484,289 bytes and SHA-256 is
`4e1c1ee22da53f0dec86b9a63fbf9d840abb11d1d60ffdf930e34d8ef9d796dd`. The
rectangle is a display window, not a legal or validated Kochi boundary. The
original source is unchanged.

This derivative is integrated as an optional categorical **context** layer
for flood, cyclone, landslide, heatwave, drought and existing compound
selections. Its source year, class legend, CC BY 4.0 attribution and limitations
are shown in the map. It is not used to calculate hazard, population,
imperviousness, exposure, vulnerability or consequences. The full acquired
tile remains an experimental raw source; only the processed display derivative
is used by the app. It does not close any of the drainage, building, population,
local hazard, or independent validation data gaps.

## NOAA IBTrACS cyclone track acquisition (2026-11-02)

The official NOAA NCEI [IBTrACS Version 4r01 product page](https://www.ncei.noaa.gov/products/international-best-track-archive)
lists a directly downloadable North Indian Ocean basin CSV. The original
27,898,552-byte response is preserved at
[`data/raw/ibtracs/ibtracs.NI.list.v04r01.csv`](../data/raw/ibtracs/ibtracs.NI.list.v04r01.csv).
Its source URL is
`https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r01/access/csv/ibtracs.NI.list.v04r01.csv`;
the [dataset DOI](https://doi.org/10.25921/82ty-9e16) and checksum/QA metadata
are recorded in the adjacent sidecar and provenance register.

The reproducible validator reports 62,891 records, 174 columns, 1,860 storm
IDs, observation timestamps spanning 1842–2026, and coordinate bounds from
87.7° W to 163.7° E and 0.7° to 83.0° N. It found no missing required
timestamps/coordinates, invalid coordinate ranges, duplicate SID/time keys,
or key-variable unit mismatches. The basin field contains 57,880 `NI`,
4,529 `WP`, and 482 `NA` rows; the file therefore includes storm observations
outside the nominal North Indian basin. A great-circle QA search found 500
points from 69 storm IDs within 300 km of a fixed Kochi reference point.
That radius is only a data-coverage check, not an impact threshold, landfall
definition, or risk estimate. The source archive combines agency best-track
records and conventions; it does not supply local wind exposure, storm
surge, flood, damage, or consequence labels.

**Rights gate:** The NCEI product page gives citation instructions, but the
inspected DataCite DOI metadata had an empty rights list and no dataset-level
licence was found. Consequently the original is locally acquired and
structurally validated, but is **not integrated into the application or
redistributed**. The next action is to obtain explicit reuse/redistribution
confirmation from NOAA NCEI and retain that response in provenance before any
map integration.

Incremental acquisition counts for this dataset: **discovered 1; downloaded
1; validated 1; integrated 0; partially verified 1; unavailable/requiring
permission 1 for application integration**. “Partially verified” here means
the source, bytes, schema, coordinates, temporal coverage and units were
checked, while rights and event-level suitability remain unresolved. It is
not independent cyclone/consequence validation.
