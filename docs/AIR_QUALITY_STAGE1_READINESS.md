# Air-quality Stage 1: dataset readiness audit

The Air Pollution page now uses a read-only readiness audit before displaying
its existing historical summaries. The audit is designed to explain what the
repository actually contains, what passed integrity checks, and which evidence
gaps still prevent stronger analysis.

## Run the audit

From the repository root:

    python -c "from pathlib import Path; from src.air_quality_readiness import audit_air_quality_datasets; import json; print(json.dumps(audit_air_quality_datasets(Path('.')), indent=2))"

Run the focused tests:

    python -m pytest -q test_air_quality_readiness_audit.py test_air_quality_readiness.py test_air_quality_monthly_reports.py

The audit is read-only. It does not download files, change hashes, overwrite
processed datasets, calculate AQI, or create a pollution forecast.

## Current dataset interpretation

| Dataset | Current status | Permitted use |
| --- | --- | --- |
| KSPCB annual AQI summaries | Provisional | Descriptive year-labelled AQI summaries |
| KSPCB daily AQI report, 16 October 2026 | Provisional | Historical report context |
| KSPCB daily station-status report | Provisional | Monitoring availability context |
| Eloor CAAQMS, August 2026 | Provisional | Historical daily descriptive summaries |
| Eloor CAAQMS, September 2026 | Provisional | Historical daily descriptive summaries |
| KSPCB NAMP Ernakulam report | Unsuitable for concentration analysis | Archive/source-table review only |
| CPCB real-time AQI feed | Unavailable | No live readings displayed |

The monthly Eloor extracts have source-hash, row-count and schema checks. Their
quality flags remain unassessed, and the exact averaging intervals and verified
station coordinates are absent. A passed integrity check does not mean that a
measurement is independently quality-certified.

The NAMP extract is retained because the source report contains useful raw
fields, but its concentration units and coordinate reference system are not
stated. The values therefore remain excluded from concentration trends and
mapping.

The daily report's station-status table includes stations marked insufficient
data or power failure. Missing readings are never converted to zero.

## Stage 1 acceptance boundary

- Report each processed dataset separately.
- Check required columns, recorded row counts and SHA-256 hashes where supplied.
- Preserve the source date range and the source's original limitations.
- Keep missing feeds distinct from files that exist but are unsuitable for a
  proposed analysis.
- Keep forecasting eligibility false until independently validated, suitably
  timed and sufficiently complete pollutant observations and labels exist.

This audit is a data-readiness report, not an AQI forecast, health assessment,
industrial source-attribution result, or probability model.
