# Scientific limitation-resolution programme

This document tracks the five open limitations as engineering and evidence gates.
A code path being implemented is not the same as a trained, validated model.

## Current verified baseline

- The Geul archive is a licensed simulation archive. The current audit covers
  six intervention scenarios for a matched model/event/return-period slice.
  The audit found repeated feature identifiers/geometries and deliberately
  does not validate a building-level damage aggregation.
- Observational and randomized intervention-effectiveness training code exists,
  but no verified physical-intervention episode dataset has passed its gates.
- Kochi has a panel template and a design-readiness audit, not an assembled
  treatment/outcome panel.
- Population exposure has an upload-driven calculator and a new GeoTIFF-to-
  GeoJSON preparation utility. No validated Kochi boundary + population raster
  pair has yet been processed and independently checked.
- Impact outputs and exposure screening are not validated against a complete
  observed disaster impact dataset.

## Workstream A — Geul simulation emulator

**Goal:** learn a surrogate of the published SFINCS simulation outputs while
keeping it explicitly separate from real-world causal intervention analysis.

Required work:
1. Inventory every scenario, forcing, model, event, return period, raster,
   building output and workbook section in the archive.
2. Verify paired baseline/intervention grids, transforms, CRS, NoData masks,
   forcing equivalence and intervention definitions.
3. Build sample rows from spatial blocks, not randomly sampled neighbouring
   pixels. Keep complete storm/event groups together for validation.
4. Use physically interpretable predictors available before the simulated
   intervention outcome (e.g. baseline water depth and verified terrain/
   exposure covariates). Do not use the target intervention raster as an input.
5. Compare a simple baseline with tree-based surrogate models. Report MAE,
   RMSE, bias, R-squared where meaningful, threshold classification metrics,
   and spatial/event holdout performance.
6. Quantify uncertainty and reject extrapolation outside training support.
7. Save a model card stating the exact Geul domain, scenarios, event coverage,
   spatial resolution, assumptions and simulation-only status.

**Release gate:** no model is called validated until it passes a held-out
storm/event evaluation and a spatial-block evaluation, with no train/test
spatial leakage. If the archive does not contain enough independent events,
report a limited within-archive emulator or refuse general validation. Never
present Geul simulation results as Kochi predictions.

## Workstream B — real-world intervention-effectiveness ML

**Goal:** estimate the effect of one clearly defined intervention on one
comparable observed outcome, within a named hazard and study population.

Required work:
1. Obtain licensed, documented episode-level observations or a defensible
   repeated site/event panel with treatment timing, treatment version,
   comparison sites, pre-treatment covariates and post-event outcomes.
2. Preserve source permissions and a provenance sidecar. Do not train on
   scraped narrative claims, synthetic fixtures, modelled Geul outputs, or
   outcomes reconstructed from press coverage.
3. Keep physical mitigation, early warning, evacuation, cash support and
   recovery assistance as distinct treatment classes.
4. Validate overlap, pre-treatment balance, missingness, outcome comparability,
   treatment timing and likely spillovers.
5. Use a design appropriate to the data: randomized assignment where valid;
   otherwise a carefully specified panel/event-study or observational
   doubly-robust estimator with sensitivity analysis.
6. Use temporal and geographic holdouts. Report uncertainty, negative controls
   where possible, pre-trend diagnostics for difference-in-differences, and
   independent replication.
7. Keep the UI ranking withheld unless evidence gates pass. A point estimate
   alone cannot establish the best intervention.

**Release gate:** a real-world model needs real observed intervention/outcome
records, a defensible identification strategy, external validation and expert
review. Restricted microdata requires authorized access; public aggregate
reports are useful evidence but are not substitutes for individual/site-level
training rows.

## Workstream C — Kochi intervention causal evidence

**Goal:** evaluate specific completed works, such as drainage/canal interventions,
against comparable locations and observed flood events.

Required records:
- geocoded intervention footprint, exact intervention version and asset/site;
- work order, start/completion dates, commissioning and maintenance history;
- site/event rainfall, tide, river/canal level and drainage conditions;
- observed inundation depth/duration and a consistently defined damage outcome;
- treated and comparison locations with repeated pre- and post-intervention
  events; and
- source references, units, quality flags and missingness.

The panel audit is only a design-readiness screen. A ready panel still needs
pre-trend checks, confounder review, spillover analysis, event-study design and
independent review. Before/after comparisons alone do not establish causality.

## Workstream D — Kochi population grid

**Goal:** make exposure screening reproducible with public, attributable data.

1. Acquire a documented 2025 GHSL population GeoTIFF candidate (100 m where
   available), recording the exact epoch, resolution, CRS, band semantics and
   licence. WorldPop Global2 is an alternative after its exact year-specific
   file and release statement are checked.
2. Reconcile the Kochi Corporation boundary and current ward polygons against
   authoritative records. Do not silently treat a community boundary candidate
   as official.
3. Run scripts/prepare_population_grid.py to clip and prepare population
   cells, retain NoData gaps and emit coverage/provenance metadata.
4. Compare the grid's city/town aggregate with Census of India 2011 PCA data
   using geographically matching units. Explain the epoch mismatch; do not
   automatically force totals to agree.
5. Only produce ward summaries after the ward layer is validated and the
   population grid's coverage and aggregation are checked.

**Release gate:** a Kochi exposure result needs an accepted boundary, a
licensed source grid, complete/quantified coverage, a census aggregate check,
and a validated hazard footprint. It remains an exposure estimate, not a
casualty forecast.

## Workstream E — observed disaster-impact validation

**Goal:** validate people/assets/damage outputs against observed event records.

Required labels include geocoded affected households or population counts,
asset inventories and observed damage by event, inundation depth/duration,
evacuation/shelter records where lawfully available, and consistent event
boundaries. Each record must identify source, date, geography, unit and
uncertainty.

Evaluation must hold out entire events and, where possible, geographic areas.
For population and building exposure, report absolute/relative error, coverage,
calibration and subgroup/ward error where reliable. Separate exposed people,
affected people, displaced people, casualties and damaged buildings; these
are not interchangeable labels.

**Release gate:** no "people affected" or "buildings damaged" prediction is
called validated until matched observed labels and independent event/geography
holdouts exist. Until then, label outputs as screening or scenario estimates.

## Operational rule

Keep the five evidence streams separate in code, registries and UI:
- Geul simulation emulator;
- observed real-world intervention-effectiveness research;
- Kochi intervention causal evaluation;
- population exposure screening; and
- observed impact prediction/validation.

No stream may silently supply labels or validation claims to another.


## Updated six-track evidence resolution — 2026-11-07

A new source audit is maintained at
`docs/SCIENTIFIC_EVIDENCE_SOURCE_AUDIT_2026-11-07.md`. It records the
public-source leads and the exact scientific boundaries for:

1. Flood event and district impacts (IFI-Impacts v4 and USGS GFID), while
   retaining the missing local inundation depth/duration and gauge data gap.
2. Kerala and India landslide inventories (Kerala 2018 and NRSC/ISRO), while
   refusing to treat unobserved cells as verified non-events.
3. Industrial incidents, where public statutory and annual factory reports
   are aggregate/governance evidence rather than facility-level ML labels.
4. Infrastructure outages, where KSEB SAIFI/SAIDI indicators are aggregate
   reliability measures rather than asset failure/restoration histories.
5. Intervention effectiveness, keeping licensed randomized cash-assistance
   evidence separate from simulated Geul intervention outputs.
6. Kochi Operation Breakthrough, where public project records identify works
   and milestones but do not form a site-by-event counterfactual panel.

The compound cyclone/flood workspace now exposes the relevant evidence tracks
for the selected registered hazards. This is a source-readiness improvement,
not a new forecast or trained model. Component hazards remain separate; no
joint probability, damage reduction, or causal intervention effect is inferred.

### Acceptance boundary

- Open aggregate or event inventories may improve context and data discovery,
  but they do not automatically satisfy local event labels, exposure, or
  non-event requirements.
- Licensed records remain unavailable to training until authorized access and
  a codebook/design review are completed.
- Simulation outputs remain in a separate simulation-only training/evaluation
  stream.
- A source being listed in the app is not evidence that it has been downloaded,
  parsed, licensed for reuse, or accepted for training.
- No unresolved track is marked operationally validated by this update.
