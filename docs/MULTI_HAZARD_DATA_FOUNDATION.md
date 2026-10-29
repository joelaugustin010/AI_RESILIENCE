# Kochi multi-hazard data foundation

**Status date:** 29 October 2026  
**Purpose:** Source acquisition and data-quality screening for AI_RESILIENCE. This is an evidence inventory, not a validated disaster prediction system.

## Acquired datasets and current limits

### Rainfall and river-level observations
The controlled workflow downloads the existing Kerala Surface Water / NWDP rainfall and river-level sources and records checksums, row counts and QA. Existing limitations remain active:
- Rainfall telemetry includes conflicting station-time values; the workflow preserves raw rows rather than silently averaging or deduplicating them.
- River-level gauge zero/datum and some station-to-river labels remain unresolved. A large reported level change across a long gap is not automatically corrected.
- The historical rainfall benchmark is a measurement benchmark, not a flood forecast.

### Historical flood evidence
The workflow acquires the India Flood Inventory and INDOFLOODS gauge-event inventory as historical context. District/event mentions and gauge events are not hourly flood labels, ward-level inundation truth, or a complete no-flood record.

### GSI Ernakulam landslide susceptibility
Source: [KSDMA hazard maps](https://sdma.kerala.gov.in/hazard-maps/) and the [Ernakulam GSI archive](https://sdma.kerala.gov.in/wp-content/uploads/2025/08/Ernakulam.zip).
- The archive passed ZIP integrity and shapefile-sidecar checks.
- The vector layer has three MultiPolygon records with classes High, Moderate and Low, CRS EPSG:32643.
- **All three source geometries are invalid due to ring self-intersections.**
- The project does not repair, dissolve, or spatially join these polygons. Provider clarification, source legend/scale, reuse terms, and boundary alignment are required first.
- Susceptibility is not a time-specific landslide forecast.

### IMD/RSMC cyclone best-track history
Official source: [IMD/RSMC New Delhi best-track page](https://rsmcnewdelhi.imd.gov.in/report.php?internal_menu=MzM%3D). A parsed mirror is used for private research acquisition; the original workbook was not independently downloaded in the workflow, and the underlying data remain © IMD pending terms verification.
- Mirror counts matched: 425 storms, 7,585 fixes and 656 remarks for 1982–2026.
- QA found 14 rows without coordinates, 32 rows involved in duplicate storm/time pairs, 2 position-suspect fixes and 203 date-suspect fixes.
- Source rows and flags are retained unchanged.
- A preliminary track-to-point screen found 2 storms with a non-suspect fix within 100 km and 13 within 300 km of an approximate Kochi reference point. The closest candidate fix is about 23.7 km away. This is not an impact estimate.

### USGS regional earthquake catalogue
Source: [USGS ComCat FDSN event service](https://earthquake.usgs.gov/fdsnws/event/1/).
- Queried 1970 through 29 October 2026 in non-overlapping five-year windows, magnitude 2.5+, within 1,000 km of an approximate Kochi reference point.
- 92 event records were returned; magnitude range 3.6–6.2. Two rows have invalid timestamps; no missing/out-of-range coordinates or duplicate event IDs were found.
- The query returned 5 events within 500 km and none within 300 km. **This does not mean there is no local earthquake hazard.** USGS ComCat is a multi-network catalogue with variable completeness; events below magnitude 2.5 are excluded.
- Event magnitude and distance do not predict local shaking or building damage.

### Candidate Kochi map and health-facility layers
- The candidate health-facility layer has 642 points; identity, positional accuracy and current-boundary alignment remain unverified.
- The Kochi ward KML candidate has 74 named placemarks and 83 polygon geometries; legal/current boundary alignment remains unverified.
- The KSDMA flood return-probability raster is a candidate modeled hazard layer. Band semantics, units, licence and fit for local exposure remain unresolved.
- None of these layers is approved for asset-level flood-exposure claims yet.

## Reproducibility and data handling

The GitHub Actions workflow **Acquire public disaster data** stores raw external data and audit outputs in a short-lived private artifact. Raw datasets are not committed to Git. The committed aggregate provenance and audit summary is:

- `data/reference/kochi_multihazard_acquisition_2026-10-29.json`

Each acquisition run records source URLs, retrieval time, file checksums, query parameters, row counts and limitations. Artifact expiry is not a permanent data archive; rerun the workflow to reacquire sources.

## What is needed before consequence predictions

1. Resolve source licensing and provenance, and independently verify source files/checksums.
2. Resolve rainfall conflicts, river gauge references, station identities and timestamps.
3. Obtain current authoritative Kochi Corporation boundaries and verified hospital/critical-facility coordinates.
4. Obtain flood depth/extent semantics, rainfall/river observations aligned to historical events, and independent event/no-event labels.
5. Obtain landslide geometry/legend clarification from GSI/KSDMA; do not repair invalid source polygons without provider guidance.
6. Cross-check cyclone tracks against the official IMD workbook and investigate flagged/duplicate records; acquire wind/rainfall/surge and impact evidence.
7. Compare USGS events with the India-specific NCS archive and GSI seismotectonic evidence; acquire local geology, ground-motion and building-vulnerability data.
8. Validate each hazard-specific model with time-separated or event-separated tests, uncertainty intervals, baseline comparisons and independent review.

**Current rule:** missing data are unknown, not evidence that a hazard or exposure is absent. Hypothetical scenarios are planning exercises. Numerical predictions and official warnings remain disabled until a hazard-specific model, fit-for-purpose data and independent validation justify them.
