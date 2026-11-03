# Air-quality source setup

The processed air-quality tables and their provenance metadata are tracked. The
original KSPCB AQI responses and the KSPCB and Directorate of Industries and
Commerce PDFs are not tracked. Their metadata does not identify a
dataset-specific open licence, so the original source files stay local.

To retrieve the exact reviewed source snapshots for tests, run this command
from the repository root:

```powershell
python scripts/acquire_air_quality_sources.py
```

The command reads expected SHA256 values and source URLs from committed
metadata, restricts downloads to the official HTTPS hosts, validates annual
AQI payloads, and checks both PDF signatures and pinned hashes. It writes only
the raw source files and provenance sidecars. It never rebuilds processed
datasets, replaces conflicting files, or updates expected hashes. If an
official endpoint returns different bytes, it stops and reports the expected
and received hashes; review the source before changing any pin.

The annual AQI endpoint does not state its reporting cutoff. Its values are
annual summaries, not pollutant observations or live readings. The September
KSPCB report is linked from the [KSPCB water and air quality directory](https://kspcb.kerala.gov.in/water-and-air-quality-directory).
The DIC allotment source is listed on the [official industrial areas and plots
page](https://industry.kerala.gov.in/index.php/land-infrastructure/da-dp).
Both agencies' copyright policies require accurate attribution and exclude
third-party material; confirm that the specific documents are covered before
redistributing them. See the [KSPCB policy](https://kspcb.kerala.gov.in/copyright-policy)
and [DIC policy](https://industry.kerala.gov.in/index.php/copyright-policy).

## Live model feed integration

The active dashboard page uses the no-key Open-Meteo Air Quality API at
`https://air-quality-api.open-meteo.com/v1/air-quality`, with Kochi coordinates
9.9312, 76.2673. It requests the documented current and hourly variables
`european_aqi`, `us_aqi`, `pm2_5`, `pm10`, `carbon_monoxide`,
`nitrogen_dioxide`, `sulphur_dioxide`, and `ozone`.

This is a CAMS modelled estimate on an approximately 11 km grid, not a CPCB or
KSPCB monitoring-station measurement. The page labels it as such and keeps it
separate from the historical KSPCB observations. Open-Meteo documents hourly
CAMS updates and the page caches requests for 15 minutes, refreshes every 15
minutes, and provides a manual refresh button. No API key is required for the
normal non-commercial endpoint.

The page includes attribution to [Open-Meteo](https://open-meteo.com/en/docs/air-quality-api)
and the [Copernicus Atmosphere Monitoring Service](https://atmosphere.copernicus.eu/).
If the API fails, the page shows a connection error and continues to display
the historical section; it does not relabel cached data as current.

The exact downloaded paths are listed in `.gitignore` so local test setup does
not add source documents to a commit or make `git status` appear dirty. The
test assertions still verify the recorded hashes and PDF signatures.

For the reviewed source inventory, explicit verified/provisional/unavailable/
unsuitable meanings, hash and schema checks, and current flood/air readiness,
see [Verified data ingestion and operational analysis](verified_data_ingestion.md).
Run `python scripts/audit_data_sources.py --format markdown` for a local
read-only report. The audit does not acquire files or rebuild products.
