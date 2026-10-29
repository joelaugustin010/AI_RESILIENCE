# Public data acquisition and scientific validation

**Review date:** 2026-10-29  
**Current decision:** Data acquisition is now reproducible; flood prediction remains **not scientifically validated**.

## What has been added

- `data/reference/public_data_sources.json` is a source registry containing official catalogue pages, direct resource URLs where confirmed, publishers, declared units/periods, expected research use and known limitations.
- `scripts/acquire_public_hydrology_data.py` downloads the registered NWDP CSV resources without editing their contents. It records SHA-256, retrieval time, response metadata, source URL and a validation status.
- Raw downloads default to `data/external/raw/`, and the manifest defaults to `data/external/download_manifest.json`. These files are intended to remain local/untracked unless the team deliberately decides otherwise. The script does not silently overwrite existing data; use `--refresh` to archive a previous version first.

## Run it in Codespaces or VS Code

From the repository root:

```bash
python scripts/acquire_public_hydrology_data.py --list
python scripts/acquire_public_hydrology_data.py --source kerala_sw_rainfall_telemetry_2021_2025
python scripts/acquire_public_hydrology_data.py --all
```

If the portal changes a resource URL, the script should fail visibly rather than save a web error page as a CSV. Update the source registry only after checking the official catalogue page. **Acquisition completed:** GitHub Actions successfully downloaded all three registered NWDP CSVs on 2026-10-29. The latest [public-hydrology-source-bundle with automated audit report](https://github.com/joelaugustin010/AI_RESILIENCE/actions/runs/40888067324) is about 5.4 MB compressed (about 94 MB uncompressed) and expires on 2026-11-05. It contains the untouched raw CSVs, SHA-256/retrieval manifest, acquisition log and `audit_report.json`. The raw data were not committed to Git.

## Source selection and roles

### Hydrological observations

The National Water Data Portal (NWDP / NWIC) catalogs hourly rainfall and river-level observations from the Kerala Surface Water Department. These are suitable candidates for descriptive hydrology and carefully time-aligned historical analysis after station identity, time convention, units, missingness, duplicates, coordinates and measurement reference are checked.

- [Kerala SW hourly rainfall catalogue](https://nwdp.nwic.gov.in/dataset/rainfall-telemetry-hourly-kerala-surface-water-department)
- [Kerala SW hourly river-level catalogue](https://nwdp.nwic.gov.in/dataset/river-water-level-telemetry-hourly-kerala-surface-water-department)
- [Kerala SW manual hourly river-level catalogue](https://nwdp.nwic.gov.in/dataset/river-water-level-manual-hourly-kerala-sw-godavari)

Do not treat a measured river level as flood depth without a verified gauge datum and location-specific threshold. Do not silently merge records from different stations, infer timezone, or average conflicting duplicate timestamps.

### First acquisition: findings that block immediate model training

The acquired files were inspected without modifying their raw bytes. SHA-256 hashes and retrieval timestamps are in the downloaded `data/external/download_manifest.json`.

| Source | Raw rows | Stations | Observed timestamp span | Important finding |
|---|---:|---:|---|---|
| Kerala SW hourly rainfall telemetry | 188,045 | 108 | 2021-04-07 to 2025-03-09 | 14,347 rows across 9 Ernakulam stations. Every recorded rainfall value is positive (0.5–113 mm); no zero-rainfall rows exist, and station time intervals are irregular. Missing rows must not be treated as dry hours. |
| Kerala SW river-level telemetry, all-network resource | 465,076 | 26 | 2021-05-29 to 2025-03-10 | 35,337 rows in Ernakulam, but only two listed stations. River/Basin fields are all `-`, gauge-reference fields are all zero, and the Ramamangalam Bridge longitude is 91.4725°E, outside the broad Kerala coordinate screening range. Do not use those coordinates or levels for spatial risk until the provider resolves them. |
| Kerala SW manual river-level subset | 16,005 | 6 | 2022-01-01 to 2025-03-31 | No Ernakulam stations. F.C.S. Mananthavadi has values around 711–719 m and is tagged River=Luni despite being listed in Wayanad; this is a serious station-scale/metadata warning. Exclude that station from analysis until verified. |

No duplicate station/timestamp groups were found in these three freshly downloaded files in the initial audit. That is a useful integrity check, not proof of completeness or scientific validity. The rainfall file's lack of zero values, irregular time coverage, the river telemetry's missing river/basin and gauge reference fields, and the manual file's extreme values are material limitations.

The acquisition script preserves source bytes and hashes. The audit script `scripts/audit_public_hydrology_data.py` reproduces structural, timestamp, duplicate, coordinate and value-range checks; its report is emitted by the acquisition workflow. All files remain marked raw/unvalidated until a separate review approves specific fields and stations.

## Independent flood-event and inundation evidence

- [KSDMA Crowd Sourcing Flood 2018](https://sdma.kerala.gov.in/crowd-sourcing-flood-2018/) reports around 13,000 inundation-depth points collected across Kerala. The public page/map is useful evidence that observations exist, but the raw machine-readable point data, coordinate precision, measurement metadata and reuse terms still need to be verified.
- [KSDMA Hazard Maps](https://sdma.kerala.gov.in/hazard-maps/) links district flood-hazard/exposure PDFs and historical flood-return-probability raster ZIPs. These are hazard/exposure context layers, not hourly outcome labels.
- [India Flood Inventory-Impacts, 1967-2023](https://zenodo.org/records/16994648) is a candidate independently curated event/impact inventory. Its exact schema, district/time granularity and licence must be reviewed before joining.
- [KSDMA Post-Disaster Needs Assessment](https://sdma.kerala.gov.in/wp-content/uploads/2019/03/PDNA-report-FINAL-FEB-2019_compressed.pdf) documents historical event impacts. Narrative or district summaries must not be expanded into fabricated station-time labels.

## Reproducible path to an evaluation dataset

1. Download original observations and retain the SHA-256 provenance manifest.
2. Audit CSV schema, duplicate keys, conflicts, time coverage, gaps, units, station identifiers and coordinate validity without changing raw files.
3. Review the source licence and provider metadata. Record whether timestamps are local time or UTC; if not specified, preserve source strings and flag the ambiguity.
4. Obtain independent event/inundation evidence in machine-readable form. Record target definition, spatial unit, observation time/interval, collection method, uncertainty and reviewer.
5. Join only after station identity and geographic matching are supported. A district-wide event is not a station-level hourly label.
6. Define the prediction issue time and future horizon before selecting features. Remove measurements or warnings that would not have been available at that issue time.
7. Use event-grouped chronological holdout, compare against a simple baseline, and report event counts, sample counts, class balance, confusion matrix, precision, recall and F1. Do not tune against the holdout.
8. If there are too few independent events, report descriptive historical evidence and data limitations rather than model metrics.

## Current scientific claim

This work improves data provenance and reproducibility. It does **not** yet create verified flood labels, establish the performance of a flood model, or authorize operational warnings. AI_RESILIENCE should continue to label any hypothetical scenario as hypothetical and direct real-world emergency decisions to official authorities.

## Additional acquisition milestone: independent IFI-Impacts tables (2026-10-29)

The acquisition registry now includes four files from the authors' [IFI-Impacts v4 Zenodo record](https://zenodo.org/records/16994648):

- `India_Flood_Inventory_v3.csv` — event-level inventory, with reported start/end dates, causes, affected districts, optional coordinates, impacts and event identifiers.
- `District_FloodImpact.csv` — district-level impact table.
- `District_FloodedArea.csv` — district-level flooded-area table.
- `DFSI.csv` — district-level Flood Severity Index table.

These sources are downloaded to the temporary workflow artifact rather than committed as raw data. The workflow records SHA-256 hashes and retrieval metadata and runs `scripts/audit_ifi_flood_inventory.py`. The audit reports table shape, missingness, duplicate rows, date parsing, coordinate completeness, and records whose reported state/district fields mention Kerala and Ernakulam.

**Licence caveat:** the record page does not clearly expose the applicable licence in the visible metadata inspected for this milestone. Keep source attribution, and do not redistribute these files until the applicable licence is verified. Download availability alone is not a reuse licence.

**Scientific interpretation:** an event record that mentions Ernakulam is only a district/event-level historical reference. It is not evidence that every ward flooded, and it is not a flood/no-flood label for each hour in the rainfall table. The district impact, flooded-area and severity tables must not be downscaled to ward-level claims without a defensible method and independent validation. The new audit deliberately does not create model labels, fill missing coordinates, or train a model.

The workflow also runs `tests/test_ifi_flood_inventory_audit.py` before acquisition to check that the audit preserves missing-data and spatial/time-granularity safeguards.

### Additional gauge-event candidate: INDOFLOODS

The registry now also includes four CSVs from [INDOFLOODS on Zenodo](https://zenodo.org/records/14584655): gauge-event periods/peak levels, gauge metadata, catchment characteristics and event-scale precipitation. The published metadata preview contains Kerala gauges, including Ramamangalam on the Muvattupuzha river, but does not show a station explicitly labelled Ernakulam. These facts make the dataset worth auditing, not automatically valid for Kochi.

The new `scripts/audit_indofloods.py` produces a descriptive report covering schema, missingness, date range, coordinates, Kerala gauge identifiers and explicit gauge/event/catchment table crosswalk gaps. The tests exercise those joins without manufacturing missing records. The audit must determine the actual event counts and coverage from the downloaded complete files.

INDOFLOODS is not a ready-made flood probability training table. Event rows alone do not provide representative non-flood windows; event-scale precipitation may include future information relative to an early-warning issue time; and matching an INDOFLOODS gauge to NWDP data requires a verified crosswalk. The source page describes access for academic/research purposes but an explicit licence was not visible in the metadata inspected; do not redistribute until terms are clarified. See `docs/INDOFLOODS_DATASET_REVIEW.md` and `docs/SCIENTIFIC_MODEL_DESIGN.md`.

