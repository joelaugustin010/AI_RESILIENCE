# Phase 2 data quality report

**Review date:** 2026-11-02  
**Quality state:** New data are research-only. The classifications below are
question-specific; a government publisher does not make a dataset inherently
verified for every use.

## Acquired snapshots

| Dataset | Authority / provenance | Completeness and internal QA | Spatial/temporal fit | Status and use |
|---|---|---|---|---|
| NWDP CWC telemetry rainfall | Portal resource metadata and source MD5 matched the downloaded bytes; portal license label is `Other (Open)` without a standard license identifier in the retrieved resource metadata. | 9,206 rows; 4 stations; no invalid timestamp/measurement rows; 1,471 duplicate station-time groups, including 324 groups with differing rainfall values. Existing project CSV has matching values on shared fields but a different schema (`_id` versus `Block`, `Village`). | Station coordinates and sampling/QC protocol are not independently validated; timestamps' timezone is undocumented. Coverage 2021-01-03 to 2025-12-28. | **Conflicting / provisionally source-matched.** Preserve all source rows; do not aggregate conflicting values or compare them to an unverified threshold. Confirm the portal's reuse conditions. |
| NWDP manual rainfall | Portal metadata and source MD5 matched. | 109,978 rows; 21 stations; no duplicate/conflicting station-time groups detected by the acquisition QA; no missing or invalid values detected by basic parser checks. | Actual coverage is 2000-02-27 to 2014-12-31, not the filename/catalog's 1991-2020 span. Local copy equals source after CSV parse; raw line endings differ. | **Provisionally source-matched, temporally incomplete for stated filename.** Descriptive history only; not a current forecast. |
| NWDP manual river level | Portal metadata and source MD5 matched. | 16,005 rows; 6 stations; no duplicate/conflicting station-time groups detected by basic QA. | Actual coverage 2022-01-01 to 2025-03-31; filename suggests 2021-2025. Gauge zero/datum and time zone are unresolved. | **Incomplete for stated filename / unverified gauge interpretation.** Never compare to danger thresholds or compare station levels as absolute elevations. |
| NWDP telemetry river level | Portal metadata and source MD5 matched. | 107,064 rows; 6 stations; no duplicate/conflicting station-time groups detected by basic QA. | Coverage 2021-06-11 to 2025-03-10; station identity/coordinates, timing, gauge datum, and telemetry QA need confirmation. | **Provisionally source-matched.** Descriptive record only. |
| IMD daily rainfall grids | Public IMD annual selection form returned NetCDF classic files; dimensions and time variables inspected. | 135 x 129 coordinate grid; all annual files have expected 365/365/366 time steps. Selected Kochi-area cell has no missing values in the three downloaded years; nationwide arrays have many fill values. | 0.25-degree cell at 10.00 N, 76.25 E nearest to fixed reference point 9.93 N, 76.27 E. Source time units are days since 1900-12-31; value units are mm. Datum/authority CRS is not identified. | **Provisionally parsed, spatially coarse, licence unresolved.** A grid estimate is not a gauge, ward exposure, flood extent, or forecast. |
| NASA POWER daily series | NASA POWER API returned valid JSON; sidecar hash and variable metadata were checked. | 1,828 dates; five expected parameters; zero fill values in this retrieved response. | Fixed point request at 76.27 E, 9.93 N; UTC dates 2020-01-01 through 2025-01-01. Grid/model values are not in-situ station observations. | **Provisionally parsed context.** No station validation or local event link. |
| OSM road snapshot | Overpass response and OSM base timestamp preserved; local SHA-256 checked. | 16,378 ways with highway tags; acquisition QA found no invalid coordinates and no ways with fewer than two points. | Rectangle is based on the observed extent of a pre-existing provisional ward file, not an authoritative Kochi boundary. OSM update/completeness varies. | **Incomplete for routing/exposure.** No road condition, flood passability, hospital connectivity, or service criticality claim. ODbL terms apply. |
| USGS earthquake query | USGS FDSN response status 200; query and returned GeoJSON preserved and hash-checked. | Zero features returned for the requested 8-12 N, 74-79 E box, 1900-01-01 to 2026-11-01, minimum magnitude 0. | Catalog scope, reporting completeness, magnitude threshold, and the wide geographic box do not determine site hazard. | **Unavailable local evidence.** Empty response is not zero hazard. No building vulnerability inference. |

NWDP portal metadata labels these four resources `Other (Open)`; no standard
licence identifier or detailed reuse terms were recorded in the resource
metadata retrieved with the payloads. Treat this as a source label, not a
substitute for confirming redistribution conditions.

## Existing project data and resolved issues

- Existing manual rainfall and river copies differ from NWDP downloads at the
  byte level because of Windows line endings, but their parsed records are
  equal. No expected checksums or observations were modified.
- The local CWC CSV contains an `_id` field absent from the source download;
  source fields `Block` and `Village` are absent from the local schema. All
  9,206 rows match across shared fields after parsing. Both schema variants
  remain unchanged, and the duplicate/conflict groups remain present.
- The KSDMA flood archive remains unsuitable pending confirmation of pixel
  meaning, NoData handling, method, return-period interpretation, attribution,
  and reuse terms.
- JRC GloFAS RP100 layers remain modelled hazard scenario evidence. They are
  not observed flood boundaries, forecasts, or proof of asset exposure.
- The NIHFW hospital dataset and provisional boundary/ward geometries remain
  ineligible for spatial joins until coordinates, geometry, currency, and
  coverage are independently checked.
- The KSPCB report/AQI evidence has dated context but not a verified
  pollutant-specific time series suitable for source attribution. Industrial
  consent/allotment documents are not emissions measurements.

## Evidence-state interpretation

The inventory uses provenance states rather than a numeric quality score.
“Source MD5 matched” means the portal and local bytes agree; it does not mean
the measurements were independently verified. “Valid geometry” only applies
to the acquisition's syntactic coordinate checks. Missing, stale, conflicting,
or spatially mismatched evidence stays explicit and does not become zero risk.

Acquisition checks do not substitute for provider QA/QC, field validation,
station records, or peer-reviewed suitability analysis. See
`DATA_GAPS.md` for the minimum evidence required before expanding analytical
use.

## Additional 2026-11-02 acquisition quality checks

The eight new source files and their SHA-256 values, source URLs, dates,
licence notes, and detailed validation outputs are recorded in
`data/raw/experimental/kochidata_2026-11-02/*.metadata.json` and
`data/reference/DATA_PROVENANCE_REGISTER.json`.

| Asset | File/schema/coverage checks | Quality finding and suitability |
|---|---|---|
| KSDMA Ernakulam flood map PDF | PDF parser read 58 pages and geospatial viewports. Pages 18–23 are Kochi Taluk maps for 10/25/50/100/200/500-year return-probability classes. Legend states flood water-level classes `<4`, `4-8`, `8-12`, `>12 m`. | Map footer states external boundaries are unverified and “Reference purpose only.” It is modeled/scenario context, not dated observed flood extent/depth/duration. Dataset licence and method details require confirmation; not integrated. |
| KSDMA statewide report PDF | PDF parser read 427 pages. Title describes historic and climate-change-induced flood hazard probability and school/hospital exposure in Kerala. | Report-level methods and outputs are not event-by-event observations. No validated local impact labels were extracted. Reuse permission not found; not integrated. |
| UNEP–KSDMA 2020 map PDF | PDF parser read 6 pages; text extraction did not establish map extent, units, event dates, or layer schema. | Presence at an official public URL does not establish local coverage, GIS semantics, or a usable event record. Not integrated. |
| GSI Ernakulam shapefile ZIP | ZIP CRC passed. One polygon layer; 3 features; `.shp/.shx/.dbf/.prj` present; CRS parses as WGS 84 / UTM zone 43N (EPSG:32643); no non-finite coordinates. | Transformed extent is 76.4091064–76.9214579 E, 9.8345281–10.3027237 N and misses the approximate Kochi review bounds. The single class field is truncated to `Susceptibi`; class definitions/scale and polygon topology are not verified. Not city evidence or integrated. |
| GSI district susceptibility PDF | PDF parser read 14 pages; extracted text includes district maps, including Ernakulam; labels say boundaries are unverified/reference-only. | A PDF map is not an authoritative georeferenced polygon or site-specific assessment. Dataset licence, scale and positional accuracy unresolved; not integrated. |
| Copernicus GLO-30 DSM | GeoTIFF read successfully: EPSG:4326, one Float32 band, 3600×3600, ~1 arc-second cells, bounds 75.9998611–76.9998611 E / 9.0001389–10.0001389 N, contains the Kochi reference point. A 100×100 window has 10,000 valid cells and values -3.039 to 21.821. | Surface model is not surveyed bare earth; vertical reference/accuracy and hydrologic conditioning are not confirmed. No local drainage model or slope/flow products were generated. Not integrated. |
| ESA WorldCover 2021 v200 | GeoTIFF read successfully: EPSG:4326, UInt8, 36,000×36,000, bounds 75–78 E / 9–12 N, 10 m nominal cells; point and 100×100 window valid. Codes in sample: 10, 30, 40, 50, 60, 80; NoData 0 absent in sample. A fixed approximate Kochi-area display crop was checksum-verified and downsampled using nearest-neighbour; its legend and class-code checks are tested. | CC BY 4.0 with attribution. The categorical 2021 layer is integrated only as a map context preview; it is not a building, imperviousness, drainage-capacity, hazard, exposure or ground-truth layer. No ward or municipal-area statistics were computed. |
| WorldPop 2025 India constrained grid | GeoTIFF read successfully: EPSG:4326, Float32, 35,040×34,507, ~3-arc-second/nominal 100 m cells; bounds 68.1958323–97.3958322 E / 6.7558336–35.5116669 N; Kochi point included. A 100×100 window has 5,354 valid and 4,646 NoData cells; valid values 0–121.1463. | Modelled constrained population is not a census observation or household count. NoData is not zero population; much of the local window may be water or outside the model mask. The source summary did not establish a dataset-specific reuse licence. No exposure totals computed; not integrated. |

### First-pass outcome

- **Downloaded:** eight originals across flood-map/report, landslide,
  terrain, land-cover and population categories.
- **Structurally validated:** all eight opened/read successfully; formats,
  checksums, CRS/extent where applicable, page/feature counts and local
  coverage tests are recorded above and in sidecars.
- **Partially verified:** rights/terms for KSDMA and GSI products; WorldPop
  dataset licence; DEM vertical reference and quality; GSI class meanings and
  Kochi coverage; KSDMA PDF event and model semantics.
- **Integrated into the application:** none. No new snapshots passed all
  application-use gates for the intended local consequence analysis.
- **Still absent:** observed flood event footprints/depth/duration,
  drainage/capacity/outfalls, event-linked rainfall/river gauge metadata,
  current authoritative asset/population/household data, and independent
  impact/outcome records. See the updated acquisition report and data gaps
  register.

## Follow-up quality review: Census and LRIS

The four official Census downloads were parsed successfully: Part A is 280
pages; Part B is 516 pages; the Kerala town workbook has three worksheets
(525 rows in `Town_3200`, including its header; 65 rows contain the
Ernakulam district name); and the Kerala village workbook has three
worksheets (1,019 rows in `Village_Data_3200`, including its header; 69 rows
contain the Ernakulam district name). Workbook table headers were read and
the catalogs establish the records' Census 2011/DCHB context. The workbooks
contain administrative codes and tabular values, not coordinates or
geometries. Values in the separate Kochi town-part rows cannot be aggregated
into a municipal total without the Census boundary and crosswalk definitions.
The village workbook has an unparseable header/footer that openpyxl ignored;
the workbook sheets and cell values were parsed, and the warning is retained
in the metadata sidecar.

The Census files are **structurally validated, but only partially verified
for application use**: the records are official and the downloads passed
document/workbook parsing, but catalog pages do not provide explicit
redistribution licences. The 2011 reference period is stale for current
exposure, and town/village coverage does not supply a current Kochi polygon
join. No Census value was added to the application or used to estimate
present-day exposure.

LRIS WMS `GetCapabilities` metadata advertises Ernakulam drains, roads,
waterbodies, and watershed layers in EPSG:4326; advertised layer bounds
intersect the approximate Kochi-area review rectangle. The service does not
expose raw data through WFS: `GetCapabilities` returns
`ServiceUnavailable` and states WFS is disabled. Advertised bounds and CRS
do not verify the feature content, accuracy, completeness, time currency, or
municipal coverage. Drainage capacity, outfalls, topology, maintenance, and
reuse permission remain unknown. No rendered image or WMS layer was promoted
to analytical evidence.

**Follow-up totals:** 4 new originals downloaded and structurally validated;
0 integrated. The four Census files and four LRIS WMS layer advertisements
are partially verified source items, not fully validated consequence-model
inputs. No new observed flood-event or event-linked impact outcome file was
obtained.
