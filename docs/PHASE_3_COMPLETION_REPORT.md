# Phase 3 scientific model implementation report

**Date:** 2026-11-02  
**Scope:** Ten exact hazard/compound selections in the current Decision
Workflow. The milestone is **implemented as evidence-gated screening and
scenario models, not as ten validated local risk predictions**.

## Exact existing selections

1. Flood
2. Cyclone
3. Earthquake
4. Landslide
5. Heatwave
6. Drought
7. Industrial incident
8. Infrastructure failure
9. Compound: cyclone + flood
10. Compound: heavy rainfall + drainage failure

No option was renamed, removed, reordered, or replaced.

## Implementation summary

- Created `src/disaster_models/` with ten individually callable model modules
  and a strict dispatcher preserving the exact workflow option strings.
- Implemented rainfall/runoff arithmetic and conditional Rational Method
  capacity comparison; cyclone wind conversion and dynamic-pressure indicator;
  reported MMI description; landslide rainfall context with no local threshold;
  NWS heat-index screening; station-level SPI-1 for >=30 complete monthly
  years; unit/averaging-matched pollutant comparison; qualitative
  infrastructure FMEA/dependency review; and two distinct compound workflows.
- All models return a common structured report with assessment class, inputs,
  method, indicators/status, consequence pathways, population/infrastructure
  evidence state, three-phase actions, dataset relevance, uncertainty, gaps,
  sources and validation status.
- Added model-specific optional inputs to the existing Decision Workflow.
  The shared workflow, scenario comparison, action budget, evidence inventory,
  existing pages and prior data context remain.
- Compound cyclone/flood indicators remain separate; interaction evidence is
  unresolved. Heavy-rainfall/drainage comparison uses only explicit scenario
  inputs and does not claim actual inundation.
- No model produces a validated prediction. No hospital, road, population,
  pollution-source, damage, fatality or service-impact estimate is asserted.

## Data use

The model modules expose Phase 2 dataset relevance and reasons for not joining
those snapshots to arbitrary user locations. Actual assessment calculations
use only explicit values supplied for that assessment, because NWDP conflicts,
fixed-point gridded products, incomplete coverage, unverified geometry and
missing local validation prevent safe spatial/time joins. Drought SPI accepts
user-supplied monthly data and requires a complete 30-year record; none of the
current local snapshots qualifies as a validated reference series.

For exact inputs, dataset status and methodology, see
`DISASTER_MODEL_METHODOLOGY.md`, `DISASTER_MODEL_INPUTS_AND_OUTPUTS.md`,
`DATA_TO_MODEL_MAPPING.md`, and `MODEL_LIMITATIONS.md`.

## Consequences, recommendations and reports

Population counts and asset nominations are explicitly marked
user-supplied/unverified. No geospatial exposure, healthcare demand, damage,
environmental impact, or economic loss is computed. Hazard-specific actions
are supplied for before/during/after conditions, remain unranked, identify
triggers and required authority/evidence, and never replace official
instructions. CSV/HTML workflow reports now serialize the full structured
assessment and compound component outputs.

## Validation status

Software tests exercise all ten model contracts, core equations, input bounds,
missing/invalid data, SPI completeness and parser, heat-index reference case,
matched pollutant units/period, compound separation, and drainage capacity
comparison. These are implementation tests only. No historical event outcomes
were spatially/time matched, so **historical validation is incomplete for every
model and predictive accuracy is not established**. See
`MODEL_VALIDATION_REPORT.md`.

Final verification on 2026-11-02:

- Focused model and workflow tests: **54 passed, 13 subtests passed**.
- Full repository test suite: **196 passed, 28 subtests passed**.
- Python compile check for the model package, workflow modules and related
  tests: passed.
- Streamlit headless smoke check: application root and `/_stcore/health` both
  returned HTTP 200; the local process was stopped afterward.
- `git diff --check` reports trailing blank lines at EOF in the pre-existing
  modified files `assessment.py` and `src/flood_risk.py`. Those unrelated
  files were not edited to avoid changing preserved work.

## Git and preservation

The worktree began with team-sensitive modified/untracked work and remains on
`main` with the previously observed two commits ahead and 219 behind its local
`origin/main` tracking ref. No fetch, synchronization, staging, commit, reset,
clean, merge, rebase, or push was performed. Existing source/data and completed
Phase 1B/2 work were preserved. Current ownership conflicts remain unresolved.

## Exact completion boundary and next step

The ten hazard-specific software assessments and UI integration are complete
within this evidence-limited scope. The requested milestone cannot be
scientifically described as ten locally validated disaster impact models:
required event data, hazard footprints, exposures, vulnerability functions and
independent outcomes are missing.

Next, obtain provider-confirmed gauge metadata and resolve the NWDP rainfall
conflicts; acquire current licensed municipal boundary, drainage, facilities,
utilities and population data; establish hazard-specific, independently
reviewed historical event/outcome sets; and validate each method with domain
experts before any local severity classification, operational warning, or
consequence estimate is enabled.
