# Verified Kochi Data Foundation — evidence status

**Status: NOT APPROVED FOR MAP OR MODEL TRAINING**
**Pull request:** #6 — keep draft and unmerged.

This report separates verified acquisition/structure checks from scientific and legal validation. A green acquisition workflow means files were retrieved and structural checks passed; it does not certify suitability for exposure analysis or model training.

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
- [x] Python tests passed on commit 37b8bd2e4676d32532b348e51f22f8ba38e5182d (run #84).
- [x] Raster ZIP integrity and basic technical metadata checked.
- [ ] Verify and checksum the 2024 Cochin boundary geometry against official notification.
- [ ] Reconcile all 642 facility candidates and duplicate-coordinate groups.
- [ ] Establish raster pixel semantics/units and reuse terms from authoritative matching documentation.
- [ ] Complete hydrology dataset provenance, quality, licence and leakage audits.
- [ ] Run spatial QA against the verified boundary and rerun complete tests after implementation changes.
- [ ] Human review of evidence; only then consider closing the data-foundation milestone.

**Current decision: remain draft/unmerged.** Automated tests passing is necessary but not sufficient for scientific validation.
