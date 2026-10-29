# Verified Kochi Data Foundation — evidence status

**Status: NOT APPROVED FOR MAP OR MODEL TRAINING**
**Pull request:** #6 — keep draft and unmerged.

This report separates verified acquisition/structure checks from scientific and legal validation. A green acquisition workflow means files were retrieved and structural checks passed; it does not certify suitability for exposure analysis or model training.


## Multi-source flood evidence fusion (29 October 2026)

A reviewed source inventory is now stored in `data/reference/flood_evidence_sources.json` and consumed by `src/evidence_fusion.py`. It records distinct evidence families rather than treating one raster or one station feed as sufficient:

- KSDMA historical flood-return raster and official Ernakulam district hazard maps (context only until the exact product supports the requested spatial scale and raster semantics are resolved).
- CWC rainfall observations (raw station-time conflicts, missingness and time alignment must be handled).
- CWC river observations (gauge datum/reference and station identity must be established before threshold comparisons).
- EIDC Kerala rainfall depth-duration-frequency estimates (mm, 0.12-degree grid, 1979–2020; catalogue says no licence provided).
- EIDC Kerala gridded flood-frequency estimates (peak discharge in m³/s on a river-network grid; catalogue says no licence provided; not local inundation depth).
- IMD forecast/warning products (not yet integrated; issue time, valid time, product and local coverage must be captured).
- Terrain/drainage/infrastructure evidence (no validated Kochi layer is currently enabled in the model).

The new evidence gate checks registry approval, source-family independence, finite numeric values, units, explicit timezone, age window and verified location/quality flags. Duplicate records or a second record from the same source family do not count as independent corroboration. The gate is deliberately **not a risk score** and never converts missing evidence into zero. A passing multi-source gate would permit only a research review, not an operational prediction.

The current registry marks all sources as unapproved for automated numerical fusion because their unresolved conditions are real. This is a concrete model improvement: it provides a transparent path to adding independently checked sources without falsely implying the existing five-row demonstration dataset is trainable. The source inventory is visible in the Flood Model Readiness page. Tests are in `test_evidence_fusion.py`.

Authoritative catalogue references:
- KSDMA hazard maps: https://sdma.kerala.gov.in/hazard-maps/
- EIDC rainfall depth-duration-frequency data: https://catalogue.ceh.ac.uk/documents/4a08e6f1-e508-4bb6-b571-b3145dd1588e
- EIDC flood-frequency data: https://catalogue.ceh.ac.uk/documents/cba9f9db-4706-4f1e-aaf4-fd7769e00db0
- IMD official weather portal: https://mausam.imd.gov.in/
- Bhuvan geospatial portal: https://bhuvan.nrsc.gov.in/

## 1. Kochi boundary

- The official Delimitation Commission ward-map portal describes the 2024 delimitation process and identifies Information Kerala Mission as technical support: https://wardmap.ksmart.live/
- The official Kochi Corporation delimitation page links to a Cochin ward map: https://kochicorporation.lsgkerala.gov.in/en/delimitation-commission-kerala-notification/590
- A direct JSON sibling endpoint tried by the acquisition workflow returned HTTP 404.
- A potentially useful independent redistribution is Vonter's Kerala wards release dated 19 November 2024. Its release notes cite the Delimitation Commission, Kerala as source: https://github.com/Vonter/kerala-wards/releases/tag/19-nov-2024 . It contains statewide GeoJSON (~242 MB) and FlatGeobuf (~136 MB) assets; this is a secondary distribution, not itself the legal notification.
- Until Cochin ward features are extracted from the 2024 source and compared with the official notification, the current fallback boundary remains unverified. Do not treat the old mirror boundary as authoritative.

Acceptance evidence: source URL, release tag/date, licence or reuse terms, checksum, Cochin ward features and attributes, geometry validity, CRS, unioned corporation outline, and comparison note against the official notification. If this cannot be established, block city-level spatial conclusions.

## 2. Health-facility candidates (642 records)

The latest successful acquisition retrieved 642 candidate points from 1,890 source features after state/district filtering. These are not 642 hospitals: reported categories include sub-centres, PHCs, CHCs, STHs and district hospitals.

Recorded checks from the previous acquisition artifact: invalid point geometries 0; district-filter mismatches 0; missing facility names 0; duplicate coordinate groups 64 involving 213 rows; exact/substring name matches against the Kerala Health Department 2024–25 institution PDF 146 of 642. Name matching is preliminary, not authoritative identity matching; aliases and abbreviations can cause false negatives.

Candidate source: Esri India Living Atlas health layer; currency, licence and provenance need review: https://livingatlas.esri.in/server/rest/services/LivingAtlas/IND_Health/MapServer/0
Independent reference list: https://health.kerala.gov.in/index.php/institutionSearch
Reference PDF: https://health.kerala.gov.in/assets/backend/uploads/Galleryitem/17506790021511401637.pdf

Duplicate coordinates do not prove duplicate institutions (multiple services may share a campus); different coordinates do not prove different institutions. Identity reconciliation needs normalized names, facility type, address/local body, coordinates and source IDs. After a verified Kochi boundary is available, rerun point-in-polygon and manually review borderline/outside points. Do not publish a definitive most-vulnerable-hospital result from the current list.

## 3. KSDMA flood-return raster

Official KSDMA hazard-map page lists historical-data return-period raster archives and attributes the work to UNEP, UN GRID, CIMA Italy, KSDMA (2020) and a 2024 assessment by RMSI and the National Insurance Academy: https://sdma.kerala.gov.in/hazard-maps/

The acquired ZIP passed integrity checks and contains 10-, 25- and 50-year GeoTIFF candidates. Prior technical audit found EPSG:4326, one float32 band per file, statewide extents, and no explicit band units or semantic descriptions in raster metadata. Sampled values were approximately 4.05–1701 (10-year), 0.6561–1974 (25-year), and 0.729–1981 (50-year); these are sampled values, not guaranteed full-raster extrema.

KSDMA's Flood Probability Report explains return periods and describes flood-hazard modelling, but that does not independently establish the exact meaning and units of every pixel in this downloaded raster variant: https://sdma.kerala.gov.in/wp-content/uploads/2022/06/Flood-Probability-Report-2022_Final.pdf

Decision: do not label pixel values as depth, water level, or annual probability based only on filenames or a related report. The KSDMA page establishes provenance context but does not by itself resolve pixel-level units/semantics or a specific licence for redistribution. Keep raster status METADATA_READ_NOT_APPROVED_FOR_MAP_OR_EXPOSURE_ANALYSIS until matching technical specifications, value interpretation, and reuse terms are confirmed. Do not silently rescale or reinterpret values.

## 4. Remaining hydrology datasets

Audit rainfall, gauge/water-level or flood-frequency datasets independently before modelling. For each, record publisher, stable source URL, retrieval date, observation period, licence, units, temporal interval, CRS, coverage, station/gauge identifiers, missingness, duplicates, coordinate validity, timestamp/time-zone handling, quality flags, alignment to Kochi and prediction time, and leakage risks. Distinguish observations from modelled estimates, return-period quantiles and hazard classifications.

A related rainfall depth-duration-frequency dataset hosted by the Environmental Information Data Centre states units of mm and a 0.12-degree grid, but its catalogue says no licence provided. Do not assume redistribution or use terms: https://catalogue.ceh.ac.uk/documents/4a08e6f1-e508-4bb6-b571-b3145dd1588e . It is a possible supplementary source, not a replacement for validating current files.

## 5. Gate checklist

- [x] Acquisition workflow completes and records provenance.
- [x] Previous full Python test workflow #40903978424 passed on commit 20a29285b2bd16de08bb6e6bfbba1f5903390089. Later map-audit code added new geometry dependencies and tests; see Section 8 for the latest run status. Passing tests are software evidence only.
- [x] Raster ZIP integrity and basic technical metadata checked.
- [ ] Verify and checksum the 2024 Cochin boundary geometry against official notification.
- [ ] Reconcile all 642 facility candidates and duplicate-coordinate groups.
- [ ] Establish raster pixel semantics/units and reuse terms from authoritative matching documentation.
- [ ] Complete hydrology dataset provenance, quality, licence and leakage audits.
- [ ] Run spatial QA against the verified boundary and rerun complete tests after implementation changes.
- [ ] Human review of evidence; only then consider closing the data-foundation milestone.

**Current decision: remain draft/unmerged.** Automated tests passing is necessary but not sufficient for scientific validation.


## 6. Follow-up review of the latest acquisition artifact (29 October 2026)

The successful acquisition workflow artifact was downloaded and its JSON audit outputs and source manifests were inspected. This adds evidence about the data limitations; it does **not** promote the datasets to approved model inputs.

### Hydrology audit findings

- **Rainfall telemetry:** 188,045 rows across 108 stations and 15 district labels. Parsed timestamps are valid and no duplicate station/timestamp groups were detected by the current audit. However, source timezone is not established, there are no zero-rainfall observations, and many stations have very long gaps. Missing hours must not be interpreted as zero rainfall.
- **River-level telemetry:** 465,076 rows across 26 stations. The audit flags 21,230 rows outside its broad Kerala coordinate screen, all associated with RAMAMANGALAM BRIDGE at longitude 91.4725; this is a serious location-quality failure, not something to silently correct. Exclude that station from spatial/predictive use until the source provider confirms the correct coordinate. Gauge-reference fields are constant across the file and their datum/meaning remains unresolved.
- **Manual river levels:** 16,005 rows across six stations. The F.C.S. Mananthavadi readings are approximately 710.695–719.126 m. These may reflect a station/reference datum rather than flood depth; do not treat them as flood depth or compare across stations until the provider documents the datum and threshold semantics.
- **IFI-Impacts inventory:** 6,876 event-inventory rows, plus district-level tables. The audit is descriptive only. District-level values cannot become ward- or station-hour labels. Applicable reuse/licence terms were not clearly established in the visible source metadata, so do not redistribute these files until terms are verified.
- **INDOFLOODS:** 4,548 event records; the crosswalk finds 531 event rows associated with Kerala gauge prefixes. There are 214 gauge metadata rows, of which 59 are marked restricted, and 59 metadata gauges have no catchment-table entry. Do not use restricted gauge records. Event-scale precipitation windows may leak future information unless their timing is proven to precede the forecast issue time; event records alone do not provide representative non-event samples.
- These are source-quality findings, not evidence that a Kochi-specific flood predictor is trained or validated. The current sources do not yet establish target labels, time alignment, local representativeness, or a defensible evaluation design.

### Additional 2024 ward-boundary source identified

A secondary open-data repository, Kerala Open Maps, documents that its ward layer is sourced from the 2024 Delimitation Commission material and is distributed under ODbL. Its README also warns that its local-government boundaries come from a different source/vintage and may not perfectly align with the 2024 ward boundaries. This is a promising candidate for extracting Cochin ward features, but it is not the official notification itself and does not alone prove that the current corporation outline is legally or geometrically verified.

- Official delimitation portal: https://wardmap.ksmart.live/
- Official Cochin Corporation notification page: https://kochicorporation.lsgkerala.gov.in/en/delimitation-commission-kerala-notification/590
- Secondary open-data repository and licence statement: https://github.com/DonLillykuttyThomas/Kerala_Open_Maps
- Repository caveat: ward and local-government boundaries can differ in source vintage and may not align perfectly.

### Updated acceptance decision

- [x] Inspect the latest successful acquisition artifact and its generated audit reports.
- [x] Identify a potential 2024 ward-boundary distribution with stated ODbL terms and record its known alignment caveat.
- [x] Identify and document high-risk hydrology quality flags, including the out-of-region telemetry coordinate and unresolved station datum.
- [ ] Extract the Cochin 2024 ward features, validate geometry/CRS, compute a corporation outline and compare it against the official notification/map.
- [ ] Obtain provider confirmation or authoritative metadata for the telemetry coordinate and river gauge datums.
- [ ] Verify source-specific licence/reuse terms for Esri health features, the KSDMA raster archive and historical flood inventories.
- [ ] Reconcile candidate health facilities against a current official source with identity and coordinate evidence; duplicate-coordinate groups need review, not automatic deletion.
- [ ] Complete spatial QA with the verified boundary, test time alignment/leakage and independent target labels, and obtain human review.

**Decision remains NOT APPROVED FOR MODEL TRAINING OR VERIFIED EXPOSURE CLAIMS.** Software CI passing is a useful code-quality signal only. This report deliberately does not call the milestone complete while source-level legal, geographic and scientific questions remain unresolved.


## 7. Additional Kochi boundary candidate located (29 October 2026)

A separate catalogue entry was found for **"Kochi Wards Map 2024"**, described as a 74-ward Kochi Municipal Corporation KML. The catalogue reports a public-domain licence, credits the source as Esri Living Atlas, and shows the resource was updated in November 2025. This is a potentially useful independent candidate for comparison and may be more targeted than downloading the full statewide ward layer.

- Dataset page: https://data.opencity.in/dataset/kochi-wards-map
- Resource metadata: https://data.opencity.in/dataset/kochi-wards-map/resource/24a3de7a-4b14-436e-ae0c-e9ec7b1749e0
- Official Kochi Corporation 2024 delimitation notification: https://kochicorporation.lsgkerala.gov.in/en/delimitation-commission-kerala-notification/590
- Official delimitation portal: https://wardmap.ksmart.live/

**Important distinction:** a catalogue's public-domain label is not proof that the file matches the final legal 2024 notification, has valid geometries, or is suitable for the project. The resource has not yet been downloaded and inspected in this workflow. Do not replace the current boundary or mark the boundary gate complete based on the catalogue description alone.

### Next boundary verification action
1. Acquire the KML with its metadata and SHA-256, retaining the raw file unchanged.
2. Parse and validate all feature geometries, coordinate ranges, ward identifiers/names, and feature count.
3. Compare ward names/counts and the unioned corporation outline against the official map/notification.
4. Record discrepancies and licence/attribution details. If comparison cannot establish a reliable match, keep the boundary gate blocked and use no ward-level exposure claims.

### Current test evidence
- Python tests workflow #86: https://github.com/joelaugustin010/AI_RESILIENCE/actions/runs/40902168189 — passed.
- Hydrology acquisition workflow #58: https://github.com/joelaugustin010/AI_RESILIENCE/actions/runs/40900447377 — passed as an acquisition run; this does not make the acquired sources scientifically approved.

**Updated decision: NOT APPROVED FOR MODEL TRAINING OR VERIFIED EXPOSURE CLAIMS.** The new catalogue entry improves the next acquisition route, but boundary verification, hospital reconciliation, raster semantics/licensing, and hydrology datum/time/label validation remain open.


## 8. OpenCity 2024 ward candidate: structural audit and geometry comparison (29 October 2026)

The OpenCity resource API returned the KML resource for **Kochi Wards Map 2024**. The latest successful acquisition run is [workflow #40906415813](https://github.com/joelaugustin010/AI_RESILIENCE/actions/runs/40906415813). The raw KML and audit metadata are in its short-lived `public-hydrology-source-bundle` artifact; the raw KML has SHA-256 `e6376e6a2ac3a0ab28615cd77f4d649bfba5c48034d26c2e31ae295697d06238`.

### Structural results

- 74 placemarks and 74 unique ward names read from the KML `ExtendedData` fields.
- 83 polygon components across the ward features; 83 coordinate rings checked.
- Zero unclosed rings, malformed coordinate tuples, or coordinates outside longitude/latitude ranges.
- Candidate extent (longitude/latitude): `[76.2370672, 9.8930813, 76.3399039, 10.0502655]`.
- The catalogue labels the licence Public Domain and credits Esri India Living Atlas. These are recorded as catalogue claims; the source's legal status and positional accuracy have not been independently certified.

### Full geometry comparison with the configured provisional boundary

The candidate ward polygons were unioned without repairing invalid inputs and compared to the existing DataMeet/Kerala OpenSDI provisional corporation polygon in EPSG:32643. Both the configured polygon and candidate union passed the geometry validity checks, but their shapes disagree materially:

| Measure | Result |
|---|---:|
| Candidate ward union area | 79.0992 km² |
| Existing provisional boundary area | 96.1376 km² |
| Intersection area | 77.3049 km² |
| Symmetric difference area | 20.6271 km² |
| Intersection over union | 0.78937324 |
| Symmetric difference / union area | 0.21062676 |

This is not a negligible edge mismatch. Approximately 21.1% of the combined union area is in the symmetric difference. The bounding boxes also differ, including an approximate 374 m difference at the southern edge, but the full geometry comparison is the stronger evidence.

**Decision:** neither geometry is promoted as the authoritative Kochi boundary. The candidate is catalogued in `data/reference/spatial_sources.json` as not integrated and not approved. The map UI now displays a warning with the comparison metrics. Do not use either geometry for definitive ward-level exposure counts until the discrepancy is resolved against the final official notification and source metadata. The official Cochin map page currently surfaced by the portal is labelled Draft Notification; that is not proof of the final legal boundary.

### Implementation and test status

- Added `scripts/acquire_kochi_ward_boundary_candidate.py` to retrieve the catalogue's actual resource URL via the resource API, preserve the raw KML, hash it, and audit ward names, rings, coordinates, extents, and geometry overlap.
- Added unit tests for malformed KML, metadata/download failure, ring/coordinate checks, bounding-box comparison, and projected geometry comparison.
- Added `shapely` and `pyproj` to `requirements-data.txt` so the full test workflow has the same geometry-comparison dependencies as the acquisition workflow.
- Acquisition workflow #40906415813 passed. The full Python test workflow is being rerun after fixing its missing geometry-test dependencies; do not treat earlier failed test runs as passing.
- These results complete a significant boundary-audit step, **not the overall map or scientific data foundation**. Remaining map blockers include official boundary/legal reconciliation, health-facility identity and coordinate verification, KSDMA raster pixel semantics/licence, and the hydrology station/datum/time-alignment issues documented above.


## Latest software verification (29 October 2026)

- Full CI: [workflow #40909191281](https://github.com/joelaugustin010/AI_RESILIENCE/actions/runs/40909191281) — **185 passed, 5 skipped, 13 subtests passed**.
- New tests cover independent source-family counting, unit/time/location/quality gates, and the requirement for feature-to-source provenance before real-observation model evaluation.
- CI success confirms software checks only. The scientific release gates above remain open, and the model continues to withhold numerical predictions.
