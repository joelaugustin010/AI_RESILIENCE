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

### What the current flood interfaces and model calculate

`pages/2_Flood_Risk.py` accepts a user-selected area, rainfall amount and
period, river reading, and ground condition. It echoes those values after a
button press; it performs no risk-score or probability calculation. The
decision workflow is qualitative and keeps user-entered observations separate
from its descriptive rainfall benchmark. Its assessment logic is unchanged;
only its stale JRC display-status sentence was corrected.

`app_pages/disaster_probability.py` audits five example rows (three positive,
two negative) dated 2026-10-19. The rows span several Kerala districts, are
marked `unverified_demo`, and have no event-group identifiers or independently
verified outcome labels. The form accepts discussion inputs but generates no
probability. The local audit blocks model fitting and inference.

`src/flood_model.py` is functioning evaluation plumbing, not a validated flood
forecast. For future eligible records it requires documented real observations,
independently verified binary labels and a 24-hour horizon, provenance and
feature-availability timing, at least 100 rows, 20 rows per class, 10 event
groups per class, five observation dates, and a chronological event-separated
holdout. Its candidate pipeline median-imputes and standardizes numeric
features, most-frequent-imputes and one-hot encodes the CWC warning category,
then fits balanced logistic regression. It compares a prior-only baseline and
reports precision, recall, F1 and a confusion matrix. The row and class floors
are engineering screening gates, not evidence of scientific validity. No
real-data fit, metric, calibrated probability or flood forecast has been
produced. The prediction helper only returns `predict_proba` from an already
fitted pipeline; it has not been fit on real observations.

The proposed 24-hour target is `target_flood_event_next_24h`. Candidate
predictors are 3-day antecedent rainfall (mm), 24-hour forecast rainfall
(mm), INSAT-3D integrated precipitable water vapour (mm), soil moisture (%),
slope angle (degrees), river-gauge height (m), gauge danger level (m), and a
CWC flood-warning category. The dataset would also need an observation date
and event-group identifier. These names and units are schema claims in an
unverified example file; they do not prove the fields are measured, aligned
in time, correctly located, or available before the prediction issue time.
Gauge and warning fields are specifically flagged for possible target leakage
until feature-availability timestamps are established.

The five-row sample is hash-consistent but lacks verified station locations,
outcome provenance, event grouping and sufficient dates or volume. Existing
hydrology rainfall and river-level files are not joined to reviewed flood-event
labels and are not inputs to an operational flood classifier. The hospital
vulnerability page previously ranked unsupported sample scores; it now states
exposure and vulnerability are unknown and lists the facility, hazard, site
data and reviewed method evidence needed before comparison. No `most
vulnerable` facility is named.

### Hazard source findings

The JRC/Copernicus GloFAS version 2.1.2 tiles are modeled river-flood depth
scenarios, not observations, coastal flooding, forecasts, warnings, or damage
estimates. The reviewed RP100 depth tiles use WGS 84 (EPSG:4326), float32,
approximately 3 arc seconds (~90 m), a `-9999` NoData value, and cover Kochi's
latitude band across adjacent 10-degree tiles. JRC documents land-only coverage
and artifacts including unrealistic depths associated with model limitations,
DEM sinks and tile boundaries. RP100 identifies a 100-year return-period
scenario in the dataset, not an exact probability for a facility and not a
forecast date. The source metadata reviewed here identifies version 2.1.2 and
tile dates in December 2025; the grid has no event-time observation period.

https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/CEMS-GLOFAS/flood_hazard/README.txt.
The README specifies Open Data Commons ODbL 1.0, while its linked copyright
notice specifies CC BY 4.0 with attribution and change indication. Both
statements permit reuse with attribution. This catalog record applies the
stricter ODbL 1.0 basis and is marked `MODELLED SCENARIO CONTEXT; LICENCE
RESOLVED; NOT OBSERVED FLOODING`. The application displays the preview only as
attributed modelled scenario context. The matching permanent-water tiles are
used solely to exclude JRC-patched water from provisional screening; the
spurious-depth artifact mask was not downloaded. See
https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/CEMS-GLOFAS/copyright.txt and
`data/raw/JRC_GLOFAS_LICENCE.md`.

KSDMA's official hazard catalogue lists Ernakulam historic and RCP 8.5 maps,
and historical 10-, 25-, 50-, 100-, 200-, and 500-year products. The local
historical 10/25/50 ZIP passes CRC validation and contains three 3004 x 5371
single-band float32 GeoTIFFs on EPSG:4326 grids with 0.000833333-degree cell
spacing and a declared NoData sentinel of `-3.402823e38`. Valid pixel ranges
are 0.729–1776.6, 0.6561–1974, and 0.729–1981 respectively. The source does
not document valid pixel units or meaning, nor dataset-specific reuse terms.
No values were thresholded, assigned a hazard class, rendered or sampled.
The bundle remains unsuitable for this proposed analysis until KSDMA confirms
pixel semantics and terms:

https://sdma.kerala.gov.in/hazard-maps/.

The KSDMA Flood Probability Report 2022 is a candidate administrative-level
source: indexed contents identify modeling methods, school/hospital exposure
mapping, and Ernakulam/local-government statistics. Its 21,992,376-byte PDF
could not be retrieved by the web tool, and no local copy was available to
inspect. No aggregate values were transcribed or treated as verified. It is
recorded as unavailable for asset-level analysis, not as a spatial point
dataset:

https://sdma.kerala.gov.in/wp-content/uploads/2022/06/Flood-Probability-Report-2022_Final.pdf.

### Asset and supporting data findings

- The NIHFW national hospital directory contributes 180 Ernakulam records to a
  source-preserving coordinate review. 149 pairs parse as two numbers, 31 are
  missing or malformed, and 18 repeated-pair groups cover 63 rows. Numeric
  range checks do not establish coordinate order, CRS/datum, correctness or
  positional accuracy. No hospital points were created.
- KITE Sametham provides school identifiers, names, administrative fields and
  some individual Google Maps links. The reviewed Ernakulam list has no
  documented bulk GIS export, coordinate semantics, accuracy, or dataset-level
  spatial reuse terms; some entries have no map link. No school points were
  created.
- The Kerala Health facility directory was inaccessible (HTTP 403) in the
  reviewed session and had no verified GIS export in the local checkout.
- KSDMA's report remains an uninspected aggregate PDF, not an asset register.
- The CWC's official meteorological-station register, dated 1 June 2012, lists
  Kalampur, Ramamangalam and Neeleeswaram in Ernakulam and prints DMS
  coordinates. The register does not state a CRS/datum or positional
  accuracy, and it does not establish current operations. It is a station
  metadata lead only; no coordinates were converted into geometry. The PDF
  was reviewed online on 2026-10-29, not downloaded, so no local file hash is
  available:
  https://www.cwc.gov.in/sites/default/files/meteorological-network-details-of-cwc.pdf.
- NWIC's Kerala Surface Water Department page lists an hourly river-level
  telemetry resource for 2026–2030, including a West flowing rivers from
  Tadri to Kanyakumari CSV. The dataset description says records contain a
  date, station identifier/geographic hierarchy, river and water level in
  metres; the page reported an update on 26 October 2026. The CSV resource
  page returned a cache-miss error and no bytes were acquired. The NWIC
  copyright policy permits accurate reproduction with prominent attribution,
  except for third-party material, but this does not verify the resource
  payload, its station semantics or resource-specific rights. No hash, rows,
  coordinates or model inputs were created:
  https://nwdp.nwic.gov.in/dataset/river-water-level-telemetry-hourly-kerala-surface-water-department
  and
  https://nwdp.nwic.gov.in/footer/copyrightPolicy.
- Ernakulam district administration's hospital and school directory pages,
  both marked last updated 15 October 2026, provide names and addresses; the
  hospital page also lists phone numbers and facility type. Its education
  page provides office contacts and school counts by level and management
  type. None of these pages exposes a reusable school/hospital GIS download
  with coordinate semantics, CRS, positional accuracy and spatial reuse
  terms; addresses were not geocoded:
  https://ernakulam.nic.in/en/public-utility-category/hospitals/,
  https://ernakulam.nic.in/en/public-utility-category/schools/ and
  https://ernakulam.nic.in/en/education/.
- LRIS 2.0 lists road network, drainage lines and canal network themes, but no
  reviewed, downloadable Kochi extract with schema, CRS, accuracy, date and
  reuse terms was obtained. Existing OSM roads and waterways are not treated
  as the municipal road or drainage inventory.
- OSM processed context passed local structural, coordinate-range and geometry
  checks: healthcare 680 features (471 points, 209 polygons), roads 13,123
  lines, waterways 2,568 lines and emergency 105 features (44 points, 61
  polygons). These are provisional ODbL community data, not complete or
  ground-truthed inventories. OSM requires attribution and share-alike under
  ODbL 1.0:
  https://www.openstreetmap.org/copyright.
- The provisional Kochi Corporation outline is self-intersecting and is not
  used as a coverage mask. The KSDMA statewide raster grid extent is not a
  flood extent. JRC tile coverage and nominal resolution alone do not establish
  complete valid-data coverage for an asset inventory.

No CRS transformation or hazard/asset intersection was performed because no
eligible authoritative hospital or school point inventory and no suitable,
reuse-cleared hazard input are jointly available. The app keeps exposure
unknown; absent map features and zero/NoData/outside-coverage cells do not mean
safe. No exact flood probability or exposed-asset count is claimed. No change
was made to decision-workflow calculations.

### Windows SciPy and test environment

The active interpreter resolves to the sibling original project's read-only
`.venv` (`C:\Users\LENOVO\OneDrive\Desktop\AI_RESILIENCE\.venv`), not a new
environment in this checkout. It reports Python 3.15.0 x64, NumPy 2.5.4,
SciPy 1.18.1, pytest 9.1.1 and Streamlit 1.66.0; the installed extension is
`scipy.ndimage._ni_label.cp315-win_amd64.pyd`. A minimal import plus
`scipy.ndimage.label` call succeeds. The earlier `_ni_label` failure therefore
was not reproduced, and its historical exception/root cause cannot be
established from the current run; no current exception was available to capture.
The extension's Authenticode status is `NotSigned`. The active site-packages
also contains SciPy's OpenBLAS DLL and NumPy's OpenBLAS and Microsoft C++
runtime DLL; the required modules loaded successfully in this run. No
SciPy/Python match was found in the
reviewed application-control log entries: 1,325 Code Integrity and 15
AppLocker EXE/DLL events were scanned with zero matches for `scipy`,
`ni_label`, or `python.exe`. A McAfee plugin block in the Code Integrity log
was unrelated. Authenticode reports the SciPy extension as unsigned, but the
current interpreter imports and executes it successfully; this does not
establish the cause of a previous failure. The Streamlit command-line
executable separately hit Windows Application Control. The devcontainer
specifies Python 3.11. Docker is unavailable. No security control was changed
and no binary was replaced. A Python 3.11 pull-request workflow is now defined
in `.github/workflows/tests.yml`.

### Supported environment and reproducibility

The repository's declared baseline is Python 3.11 in
`.devcontainer/devcontainer.json`. Python 3.11 remains in security-fix support
through October 2027, and Streamlit's installation documentation currently
lists Python 3.11–3.15. Use an isolated Python 3.11 environment to match the
configured project baseline; do not use the sibling project's Python 3.15
environment as a deployment or lockfile baseline. Python 3.11 is in security
maintenance, so plan a tested move to a newer supported minor before its
security-fix period ends:
https://devguide.python.org/versions/ and
https://docs.streamlit.io/get-started/installation/command-line.

On Windows PowerShell, create and install the project's core dependencies in
an isolated environment with:

    py -3.11 -m venv .venv
    .\.venv\Scripts\python.exe -m pip install --upgrade pip
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt
    .\.venv\Scripts\python.exe -m pip check

For optional PDF extraction, also install `requirements-data.txt`. Run the
source audit, fail-closed flood-model readiness CLI, and test suite from that
same interpreter:

    .\.venv\Scripts\python.exe scripts/audit_data_sources.py --format json
    .\.venv\Scripts\python.exe src/evaluate_flood_model.py
    .\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider

The current `requirements.txt` pins Streamlit and bounds scikit-learn, but
leaves several direct and transitive dependencies unpinned; it is not a lock
file. A clean Python 3.11 environment was created and pip was bootstrapped, but
dependency installation failed when DNS resolution for
`files.pythonhosted.org` failed while retrieving PyArrow. Resolver selections
are recorded in `docs/testing.md`; no Python 3.11 dependencies were installed
or tested. Do not treat the successful Python 3.15 test run as verification of
the Python 3.11 environment. After a clean Python 3.11 install succeeds,
capture and review `python -m pip freeze --all` as a platform-specific lock
artifact before claiming exact environment reproduction. The SciPy toolchain
compatibility table can guide that review:
https://docs.scipy.org/doc/scipy/dev/toolchain.html.

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

Run the clean-checkout-compatible suite with:

    python -m pytest -q -ra --strict-markers

The repository suite includes `test_flood_model.py`, `test_flood_raster.py`,
catalog/audit blockers, the existing decision workflow checks, and Streamlit
AppTest coverage for Data Readiness, the Kochi map, and Hospital Vulnerability.
On 2026-10-29, the available Python 3.15 interpreter completed the default
suite with 155 passed, 3 skipped, and 13 passing subtests. The skips are the
optional ignored-source snapshot checks described in `docs/testing.md`. The
local research checks were also run separately: 3 passed, 155 deselected. The
first sandboxed attempt denied fixture writes; both final runs used a writable
temporary directory within the isolated workspace. This verifies the suite in
the available Python 3.15 environment only; Python 3.11 remains unverified.

This checkout's tests are also unittest compatible:

    python -m unittest discover -s . -p "test_*.py" -v
