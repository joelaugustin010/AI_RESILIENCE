# Verified ingestion and analysis readiness

Reviewed 2026-10-29. The project keeps its existing air-quality and spatial
source catalogs in data/reference/air_quality_acquisition.json and
data/reference/spatial_sources.json. Each source has a stable dataset_id and
a canonical evidence_status; definitions are in
data/reference/data_status_definitions.json.

## Status meanings

- verified: source identity, integrity, schema, dates and spatial meaning
  support the stated limited use.
- provisional: the source or file is credible, but an important coverage,
  quality, reuse, or interpretation question remains.
- unavailable: a required source or input was not obtained or is missing.
- unsuitable: the file is invalid or cannot support the proposed analysis
  without an unsupported assumption.

Status is tied to the source's stated use. A historical permit record can be
provisional evidence of an old application while remaining unsuitable as proof
of current consent or emissions.

## Audit and reproducible processing

Run a local audit without downloading or writing data:

    python scripts/audit_data_sources.py
    python scripts/audit_data_sources.py --format json

The Streamlit Data Readiness page uses the same audit code. It checks local
file signatures, sizes, hashes, JSON schemas, metadata and aggregate HTML
structure; it also reports the status and blockers recorded in the existing
spatial and air-quality catalogs. The JSON output is suitable for other tools.
The audit never rewrites raw sources.

Raw files and sidecars remain under data/raw/ and are ignored by Git when
reuse terms are unknown. The staging snapshots were copied byte-for-byte and
SHA-256 checked. No browser profile, nested repository, cache, or invalid PDF
response was copied. Existing processed files remain under data/processed/;
their metadata records source hashes, extraction details, row counts and
limitations.

The annual KSPCB JSON summaries are validated by src/air_quality_sources.py.
Their year labels do not give an exact aggregation cutoff; the 2026 values may
be partial-year. They are statewide annual AQI indices, not timestamped
values, pollutant concentrations or a Kochi-only spatial series.

Optional PDF extraction uses pypdf:

    python -m pip install -r requirements-data.txt
    python scripts/prepare_kspcb_air_reports.py
    python scripts/prepare_kspcb_air_reports.py --write
    python scripts/prepare_new_official_air_evidence.py

The first KSPCB preparation command is read-only by default. The --write
option creates missing processed outputs only after PDF signatures and raw
hashes pass; it refuses to replace an existing output whose bytes differ. The
September 2026 CAAQMS and DIC allotment preparation script likewise verifies
raw sidecars and refuses to replace different processed outputs. Acquisition
is separate and manual: scripts/acquire_air_quality_sources.py uses reviewed
HTTPS hosts and pinned source hashes. No acquisition script was run for this
milestone.

## Recovered air-quality evidence

| Source | Coverage established | Status and permitted use | Material limits |
| --- | --- | --- | --- |
| KSPCB annual AQI JSON, 2023–2026 | Statewide station labels; 2, 46, 41 and 41 rows respectively | Provisional; descriptive year-labeled AQI summaries only | Exact aggregation cutoff and station coordinates are absent. No pollutant values or timestamps; 2026 may be year-to-date. |
| KSPCB daily AQI report | 16 October 2026; five reported station rows | Provisional; historical report values | Not a live feed. Pollutant averaging windows, completeness and coordinates are not supplied. |
| KSPCB CAAQMS reports | Eloor, August and September 2026; 31 and 30 dated extract rows | Provisional; descriptive daily ambient summaries | Printed units are retained. Exact averaging intervals, row-level QA/completeness and verified station coordinates are absent. |
| KSPCB NAMP report | Directory label August 2025; Ernakulam report pages state June 2025; 62 dated rows across eight stations | Unsuitable for concentration trend or AQI analysis | Pollutant units and CRS are not stated. Values remain preserved in the extract but are excluded from analysis. |
| KSPCB legacy CTO application listing | Query period 2015-04-01 to 2019-10-20; Edayar entries are historical application records | Provisional; historical record matching only | An application decision is not the consent certificate or a current validity record. The 4.59 MB HTML is not rendered in the app. |

The KSPCB Water and Air Quality Directory lists the monthly reports and daily
AQI products; its current page shows September 2026 CAAQMS and later daily
reports, so the local 16 October snapshot is historical, not latest:
https://kspcb.kerala.gov.in/water-and-air-quality-directory. The annual AQI
endpoint is also documented in the source catalog.

## Edayar research

- The DIC allotment register is dated 15 February 2022 in its official listing.
  It supports historical name/plot cross-checks only. Plot numbers are not
  coordinates, and a 2022 “Working” field does not prove current operation.
- The KWA Edayar CETP report was prepared in August 2021 and approved in 2022.
  It provides estate-level trade-effluent context and names major industries;
  it does not provide firm-level air emissions or verified firm coordinates.
- The DIC AutoCAD drawing begins with the AC1018 file signature and its
  sidecar records a 2021-05-25 drawing date. No compatible CAD reader was
  available, so CRS, extent, plot geometry and company-to-plot joins remain
  unverified. No coordinates are derived from it.
- The legacy HTML report is a public historical application listing. A
  structural parser found tables and rows, but the file is retained locally
  and not rendered or used to infer current consent.
- Ten purported CTO PDF files were 497-byte HTML responses with the same hash
  and no PDF signature. Their names, hash and exclusion reason are in
  data/reference/ingestion_exclusions.json; they are not evidence PDFs.

The DIC official industrial-area page links to the Edayar AutoCAD file and
dated allotment register:
https://industry.kerala.gov.in/index.php/land-infrastructure/da-dp.
The separate information-request document remains a draft and has not been
sent. The evidence checklist separates established records from hypotheses
and outstanding requests.

## Flood-analysis boundary

The existing map may show the JRC RP100 raster as modeled hazard context. JRC
describes the global river-flood grid as approximately 90 m, with water-depth
values and known modeling artefacts; this is neither a forecast nor observed
flood extent:
https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/CEMS-GLOFAS/flood_hazard/README.txt.
The JRC README states ODbL 1.0 while its linked copyright file states CC BY
4.0, so confirm applicable reuse terms before republishing:
https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/CEMS-GLOFAS/copyright.txt.

No operational asset-to-hazard counts are supported:

- The KSDMA raster archive remains excluded because its reuse terms and
  pixel/NoData semantics were not verified.
- NIHFW hospital coordinate order, CRS/datum and positional accuracy remain
  undocumented. Valid-looking numeric pairs are not treated as points.
- OSM health, road and waterway features are provisional community context,
  not complete facility, road-condition or municipal drainage inventories.
- A verified school layer and an authoritative municipal drainage inventory
  are unavailable.

The app therefore reports exposure as unknown. It does not treat missing
features or transparent raster cells as safety, and it does not claim a flood
probability, predicted loss or most-vulnerable facility. The existing
decision-workflow logic is unchanged.

## Air-quality interpretation boundary

The Eloor CAAQMS extracts can support descriptive summaries with their source
dates and printed units. Annual AQI remains an index summary, not a pollutant
concentration. The NAMP extract remains excluded because units and CRS are
missing. None of the recovered records establishes a facility's current
operations, current air consent, stack emissions or contribution to an
ambient reading.

Industrial attribution would require current facility identity and coordinates,
valid air consents, measured stack results, comparable ambient observations,
quality/completeness metadata, time-aligned meteorology and competing-source
data. Until those inputs exist, no factory ranking or causal claim is produced.

## Tests

Run the repository suite with:

    python -m pytest -q

This checkout's tests are also unittest compatible:

    python -m unittest discover -s . -p "test_*.py" -v
