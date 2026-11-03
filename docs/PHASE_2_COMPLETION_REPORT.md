# Phase 2 completion report

**Review date:** 2026-11-02
**Project:** AI_RESILIENCE, Kochi / Ernakulam
**Outcome:** Reproducible research data foundation and guarded workflow context
integration completed. This is not a validated local risk, impact, warning, or
prediction model.

## Git safety and preservation

- Current branch remains `main`; the local tracking status remains two commits
  ahead and 219 behind `origin/main`.
- Existing modified and untracked files were preserved. No fetch, pull, stage,
  commit, merge, rebase, reset, clean, push, or deployment was performed.
- The Phase 1B changes and existing data/source files remain in place. The
  existing Decision Workflow was extended with an optional, hash-checked
  research context panel; it was not rebuilt.
- Ownership of pre-existing uncommitted/untracked assets remains unknown, so
  repository synchronization still requires the ownership review and safe
  worktree strategy documented in `PHASE_1B_REPORT.md`.

## Data acquired and inventory

Eight datasets represented by ten downloaded files are preserved under
`data/raw/experimental/`:

1. Four NWIC/NWDP rainfall and river-level CSV resources.
2. IMD 0.25-degree daily rainfall grids for 2018, 2021, and 2024.
3. One NASA POWER daily JSON series.
4. One provisional OpenStreetMap road snapshot.
5. One USGS earthquake catalog query response.

The new files total **130,694,819 bytes**. Every acquired file has a sidecar
with its source, retrieval time, quality notes, and SHA-256. The regenerated
`data/reference/DATA_PROVENANCE_REGISTER.json` inventories **69** selected
repository data assets overall; **55** pre-existing assets do not have a
sidecar. This register hashes files but does not certify their provenance,
licence, accuracy, completeness, or suitability.

The four NWDP downloads matched portal-published MD5 values. Three existing
manual rainfall/river copies match after parsing and differ at byte level
because of line endings. The existing CWC rainfall file matches source values
across shared fields, but its `_id` field differs from the source's `Block` and
`Village` columns. Both variants and all 324 conflicting CWC station-time
groups remain preserved.

## Integration and scientific controls

- The existing workflow now has an optional panel for IMD daily cell values,
  NASA POWER variables, an OSM road-way count, and the USGS query result.
- Loaders verify file hashes and structural metadata before parsing. Missing
  snapshots are shown as unavailable; malformed or hash-mismatched files
  produce an explicit validation error.
- Fixed gridded points are never joined to the user's assessment location,
  provisional ward boundaries, hospitals, or flood maps. The app labels IMD
  and NASA values as coarse gridded/model-derived context.
- The OSM way count is not interpreted as connectivity, passability, or
  hospital access. The USGS zero-result query is explicitly not interpreted
  as zero earthquake hazard.
- Existing JRC/KSDMA flood evidence, hospital coordinates, air-quality
  measurements, compound-hazard dependencies, and recommendations keep their
  prior evidence gates. No risk score, probability, factory attribution,
  intervention benefit, or model accuracy was manufactured.
- No historical event validation or predictive training was performed.

## Deliverables

- Data source/acquisition/quality reports, data dictionary, data gaps,
  scientific literature review, data-to-model mapping, and this completion
  report under `docs/`.
- `scripts/acquire_phase2_data.py` for public-source acquisition, structural
  QA, and repeatable inventory generation.
- `src/phase2_data.py` for strict optional-data parsing and hash checks.
- `data/reference/DATA_PROVENANCE_REGISTER.json` and source-adjacent metadata
  sidecars for each acquired snapshot.
- `test_phase2_data_foundation.py` and expanded
  `test_decision_workflow_streamlit.py`.

## Verification results

- Full repository suite: **170 passed, 15 subtests passed**
  (`.venv\Scripts\python.exe -m pytest -q`).
- Focused Phase 2 readers plus Streamlit integration: **13 passed**.
- Python compile check passed for the acquisition script, readers, UI, and
  added tests.
- Streamlit headless startup: application root returned HTTP 200 and
  `/_stcore/health` returned HTTP 200. The test process was stopped afterward.
- Pylance reported no diagnostics in the new Phase 2 reader, acquisition
  script, or new tests. The UI retains the two previously documented
  unused-cache-key warnings in the existing historical rainfall cache helper.
- `git diff --check` reports only the pre-existing extra blank lines at EOF in
  `assessment.py` and `src/flood_risk.py`; neither file was changed for Phase 2.
- The deployed Streamlit site was not checked, and no deployment success is
  claimed.

## Limitations and completion boundary

The acquired rainfall and river values lack provider-confirmed station/time
metadata and have identified CWC conflicts. IMD reuse terms need confirmation;
its nearest 0.25-degree grid value is not a station measurement. NASA POWER is
not in-situ data. GPM IMERG requires authorized registration. The inspected
global NOAA IBTrACS CSV was not downloaded. No suitable verified drainage,
hospital/emergency, utility, population, industrial emission, or local
earthquake vulnerability layer is available. KSDMA raster meaning and reuse
terms remain unresolved. Air-quality summaries do not establish an industrial
source.

Therefore, Phase 2 completes the reproducible data foundation and exposes
supported context in the existing UI, but cannot scientifically support local
asset-level flood exposure, compound-event quantification, infrastructure
cascades, ranked interventions, or predictive claims.

## Exact next action

Obtain from CWC/NWDP the authoritative station identifiers and coordinates,
time-zone/sampling and quality metadata, gauge datum/zero, official stage
thresholds, and reconciliation of the 324 conflicting CWC station-time groups.
In parallel, obtain current authoritative Kochi boundaries, drainage, hospital
and emergency facility, population, and utility layers with documented CRS,
completeness, dates, and reuse rights. Until these are independently reviewed,
keep the new data contextual and the local conclusions unquantified.
