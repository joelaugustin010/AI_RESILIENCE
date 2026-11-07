# Alternative evidence and modelling plan

Updated: 2026-11-07

## Purpose

This milestone replaces a single missing-data strategy with several evidence
routes. Public catalogues and administrative reports are not automatically
training datasets. Data access, reuse terms, spatial coverage, metadata,
resolution, observation time and independent validation must be checked before
a source is promoted.

## Implemented research utilities

- `src/evidence_alternatives.py` contains a source registry for satellite
  flood reconstruction, landslide inventories, industrial process-safety
  screening, utility reliability indicators and Kochi intervention
  reconstruction.
- `audit_satellite_flood_geojson` validates event IDs, acquisition times,
  sensor, HTTPS provenance and polygon geometry metadata. It distinguishes
  satellite-observed extent from modelled simulation and never infers depth or
  forecast skill.
- `generate_pseudo_absence_samples` selects only supplied eligible background
  points outside a configurable buffer around mapped landslide positives.
  Its label is explicitly `PSEUDO_ABSENCE_NOT_VERIFIED_NEGATIVE`. It cannot
  establish that a location was surveyed and confirmed landslide-free.
- `assign_spatial_block_splits` assigns whole spatial blocks to train,
  validation and test. It refuses fewer than three blocks to avoid pretending
  that a spatial holdout exists.

## Evidence alternatives by gap

### Flood

NRSC/ISRO's Flood Affected Area Atlas of India describes satellite-derived
flood affected maps for 1998-2022 and multi-date progression/recession mapping.
Copernicus Data Space provides Sentinel-1 products and APIs. Use these for
historical observed inundation footprints where event coverage and acquisition
timing are adequate. Satellite water extent is not flood depth, duration at a
specific building, or a future flood probability. Preserve sensor, acquisition
time, processing method, source URL, CRS and event ID. Do not mix simulated
hydraulic outputs with observed satellite labels.

### Landslide

NRSC/ISRO reports an inventory of about 80,000 landslides mapped during
1998-2022. KSREC's SILAAS programme reports a nearly 100,000-polygon inventory
spanning 1998-2024. Bhuvan provides event-based and seasonal inventory views.
These are candidate inventory sources, not proof that all vectors are openly
downloadable or reusable. Confirm geometry access, completeness, positional
accuracy, mapping effort and licence. Pseudo-absence modelling is permitted
only as a sensitivity-tested susceptibility experiment with surveyed/eligible
background, spatial blocks, event/geography holdouts and explicit
pseudo-absence labels. Do not describe pseudo-absence as true negative.

### Industrial incidents

DGFASLI explains major-accident reporting and safety-report duties; Labour
Bureau publishes annual factory statistics. Use aggregate data for context and
trend summaries only. Build facility-specific scenario/consequence screening
from verified, lawfully supplied facility and process records. Do not estimate
facility incident probabilities from state/national aggregates or attribute
pollution to a facility from proximity/AQI alone.

### Infrastructure failure

KSEB's Urjadooth dashboard exposes system-level feeder/DTR and reliability
indicators, including SAIFI/SAIDI. Capture timestamp, dashboard scope,
definition, filters and retrieval date for every snapshot. These are
system-level operational indicators, not a substitute for asset-level failure
and restoration histories. Use them for reliability context and preparedness,
not asset-level ML failure probabilities.

### Kochi interventions

Reconstruct an evidence timeline from KSDMA's Kochi 2019 record, the Kerala
Irrigation Department Operation Breakthrough report, government orders,
work orders, as-built footprints and completion/commissioning records. Link
these to independently observed satellite flood extents and event-specific
rainfall, tide and river evidence. Technical sanction or a narrative report of
relief is not proof of completed work or causal impact. A causal estimate
requires repeated treated and comparison-site outcomes, pre-trend checks,
confounder adjustment, treatment timing, spillover review and independent
sensitivity analysis.

## Source catalogue

- NRSC Flood Affected Area Atlas:
  https://ndrf.nrsc.gov.in/documents/downloads/allindia_flood_techdoc.pdf
- Copernicus Sentinel-1:
  https://dataspace.copernicus.eu/data-collections/copernicus-sentinel-missions/sentinel-1
- NRSC Landslide Atlas:
  https://www.nrsc.gov.in/nrscnew/resources_atlas_landslide.php
- KSREC SILAAS:
  https://ksrec.kerala.gov.in/website/website_english/HomeController/silaas
- NRSC Bhuvan landslide portal:
  https://bhuvan-app1.nrsc.gov.in/disaster/usrtasks/landslide/landslide.php
- DGFASLI:
  https://dgfasli.gov.in/en/faq
- Labour Bureau factory statistics:
  https://labourbureau.gov.in/reportsonstatisticsoffactories
- KSEB Urjadooth:
  https://hris.kseb.in/oms/
- KSDMA Kochi 2019:
  https://sdma.kerala.gov.in/kochi-2019/
- Kerala Irrigation Department Operation Breakthrough:
  https://www.irrigation.kerala.gov.in/sites/default/files/2021-08/kochiflood.pdf
- Government Order 474/2024:
  https://document.kerala.gov.in/documents/governmentorders/govtorder1707202414%3A45%3A51.pdf

## Verification boundary

The functions are code-level tools, not proof that source datasets have been
downloaded or ingested. No public source is promoted to model training until
the underlying files, licence, schema, coordinates, temporal coverage and
independent validation are audited. No operational prediction or causal
intervention benefit is claimed by this module.
