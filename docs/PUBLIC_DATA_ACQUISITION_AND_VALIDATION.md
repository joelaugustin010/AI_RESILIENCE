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

If the portal changes a resource URL, the script should fail visibly rather than save a web error page as a CSV. Update the source registry only after checking the official catalogue page. The current environment used for this review could inspect the catalogue pages but could not download the CSV response directly; therefore no claim is made that new raw datasets have already been acquired by this commit.

## Source selection and roles

### Hydrological observations

The National Water Data Portal (NWDP / NWIC) catalogs hourly rainfall and river-level observations from the Kerala Surface Water Department. These are suitable candidates for descriptive hydrology and carefully time-aligned historical analysis after station identity, time convention, units, missingness, duplicates, coordinates and measurement reference are checked.

- [Kerala SW hourly rainfall catalogue](https://nwdp.nwic.gov.in/dataset/rainfall-telemetry-hourly-kerala-surface-water-department)
- [Kerala SW hourly river-level catalogue](https://nwdp.nwic.gov.in/dataset/river-water-level-telemetry-hourly-kerala-surface-water-department)
- [Kerala SW manual hourly river-level catalogue](https://nwdp.nwic.gov.in/dataset/river-water-level-manual-hourly-kerala-sw-godavari)

Do not treat a measured river level as flood depth without a verified gauge datum and location-specific threshold. Do not silently merge records from different stations, infer timezone, or average conflicting duplicate timestamps.

### Independent flood-event and inundation evidence

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
