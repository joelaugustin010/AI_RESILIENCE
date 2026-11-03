# Decision workflow: method and implementation

## Status and scope

This document describes the qualitative decision workflow used by the root
Streamlit application (`app.py`) and its Decision workflow page. It is not a
validated disaster-risk model, operational warning system, or replacement for
official emergency guidance.

The workflow is designed to organize user-provided scenario information,
surface evidence gaps, compare hypothetical planning cases, and produce
traceable action candidates. It deliberately does not assign a risk score,
probability, severity class, confidence percentage, or intervention benefit.

## Previous and current workflow

| Area | Earlier workflow | Current workflow |
|---|---|---|
| Intake | A structured multi-hazard intake already existed, but its free-text source notes and classification were not validated, and population decimals were accepted by the pure helper. | Retains the intake while validating supported input classes, finite values, rainfall-period semantics, whole-person counts, and asset-list shape. User-provided sources remain explicitly unverified. |
| Risk concepts | No explicit status for evidence supporting each risk dimension. | Reports input/provenance, data availability, hazard, exposure, vulnerability, interactions, consequences, risk, and capacity/resilience separately. |
| Hazard interpretation | The legacy `assessment.py` helper can produce a 0–3 demonstration score using fixed 100 mm and 5 m thresholds; it is not called by the connected decision page. | The connected page continues not to call that helper. Those values are not official thresholds and are not used in this workflow. |
| Compound scenarios | The “heavy rainfall + drainage failure” selection was represented as flood plus infrastructure failure. | It is represented as distinct heavy-rainfall and drainage-failure drivers. Their interaction is still not modeled; time, space, dependence, and service dependencies are identified as evidence needs. |
| Recommendations | Hazard-specific generic actions were available, without an explicit row-level link to the current intake. | Unranked candidates state the selected scenario or observed information gap that triggered them, why the candidate may help, and what evidence/authority is needed. Asset-specific actions are shown only when the corresponding asset/service was nominated. |
| Reports | Reported static rainfall/river QA findings even if their source files were absent. | Includes the current evidence inventory, assessment-dimension matrix, and evidence-linked candidates; does not assert those fixed source findings when the sources are missing. |

The current page also retains scenario comparisons, user-entered action costs
and priorities, budget arithmetic, and CSV/HTML report export. Budget fit is
not interpreted as risk reduction, effectiveness, or optimality.

## Scientific framing

UNDRR defines disaster risk as potential losses determined probabilistically as
a function of hazard, exposure, vulnerability, and capacity. This is a
conceptual relationship, not a universal instruction to multiply or add
arbitrary indicator scores. See [UNDRR, “Disaster risk”](https://www.undrr.org/terminology/disaster-risk)
(Sendai Framework Terminology, 2017; accessed 2026-11-01).

The implementation keeps the concepts distinct:

| Concept | Meaning in this workflow | What is currently supported |
|---|---|---|
| Hazard | A potentially damaging physical event or condition. | A hazard/scenario label and user-entered values. No locally calibrated intensity, likelihood, or official warning is inferred. |
| Exposure | People, assets, or services in a hazard-affected place and time. | User-nominated assets and optional population context only. No location-specific spatial join is performed by this workflow. |
| Vulnerability | Susceptibility to harm given the hazard and exposed elements. | User-described drainage/infrastructure status, when supplied. No building fragility, social vulnerability, or asset-condition model is applied. |
| Consequences | Potential impacts on people, assets, and services. | Qualitative pathways to review. Impacts, casualties, damage, service loss, and recovery time are not calculated. |
| Risk | Potential losses arising from the hazard interacting with exposure and vulnerability/capacity. | Not estimated. There is no validated local outcome target or compatible, calibrated evidence join. |
| Capacity/resilience | Ability to prepare, withstand, respond, maintain functions, and recover. | Not measured. Preparedness prompts are not a resilience score. |

No mathematical risk relationship is implemented. A numerical product, weighted
sum, or threshold would imply scale compatibility and calibration that the
available evidence does not establish. The supported output is therefore an
evidence-readiness assessment, not “low”, “elevated”, or “high” risk.

## Workflow stages

1. **Validate intake.** Reject unsupported hazard labels, blank locations,
   unknown input classifications, malformed assets, non-finite numeric values,
   invalid rainfall periods, and non-integer population counts.
2. **Record provenance status.** Inputs can be labelled hypothetical,
   user-reported, user-supplied forecast, or unknown. The label and source/time
   notes are recorded; the application does not authenticate them.
3. **Inventory evidence.** Display known local files and their documented
   coverage and limitations. File presence is not quality approval, and the
   inventory does not imply a source is used in the scenario assessment.
4. **Separate assessment dimensions.** The page and report identify what is
   supplied, what is user-described, what is not joined, and what remains
   unassessed. Uncertainty is described in text; no unsupported confidence
   percentage is created.
5. **Review hazard interactions.** Compound selections retain separate
   components. The workflow does not sum component scores. It calls out the
   missing evidence needed to establish spatial/temporal overlap, dependence,
   and cascading service failure.
6. **Compare scenarios.** Entered conditions and hypothetical service
   degradation/compound cases are clearly labelled. Their consequences are
   review prompts, not modeled impacts.
7. **Generate recommendation candidates.** Candidates link to the selected
   scenario, user-described service condition, nominated asset, or an explicit
   evidence gap. They are not ranked by risk reduction or cost-effectiveness.
8. **Compare budgets and export.** Only user-entered costs are summed; incomplete
   costs prevent a complete affordability conclusion. Reports preserve the
   inputs, evidence limitations, dimensions, scenarios, candidates, and
   arithmetic basis.

## Input fields and interpretation

| Input | Unit/constraint | Interpretation and limitation |
|---|---|---|
| Rainfall | mm; a period is required. | User-entered amount; station, timezone, quality, accumulation convention, and source are not verified. “Other” requires a description in notes. |
| River level | m; finite values, including negative values, are accepted. | Gauge values can depend on a local datum. No threshold or cross-station comparison is made; station and reference should be supplied. |
| Wind speed | km/h; finite and non-negative. | User-entered context only; no cyclone intensity, warning, or damage estimate is inferred. |
| Temperature | °C; finite, negative values accepted. | User-entered context only; no heat-health threshold or forecast is inferred. |
| Affected population | people; finite, non-negative whole number. | User-entered context; not independently verified or geospatially allocated. |
| Drainage/infrastructure status | Controlled descriptive choices. | User-reported or hypothetical condition; not an inspection, asset record, or engineering assessment. |
| Assets/services | User-selected names. | Nominated for review, not confirmed to exist at the location or to intersect a hazard footprint. |
| Source/time notes | Free text. | Recorded but not parsed, authenticated, or converted to a provenance assertion. |

## Compound-event policy

Compound hazards are not equivalent to the sum of their individual risks. The
current cases only identify component drivers and review questions. A future
compound model would require, at minimum:

- comparable event timestamps, timezone conventions, and durations;
- compatible spatial footprints and resolutions for every component hazard;
- evidence of dependence or conditional occurrence rather than an independence
  assumption;
- verified infrastructure/service dependencies and failure sequences;
- event-linked exposure and observed consequence records; and
- an uncertainty and validation design appropriate to the target outcome.

Without those inputs, no combined probability, consequence, or risk estimate is
produced.

## Evidence currently available and Phase 2 requirements

The local source registers are the authoritative inventory for this workspace:
[`data/reference/hydrology_data_sources.json`](../data/reference/hydrology_data_sources.json),
[`data/reference/spatial_sources.json`](../data/reference/spatial_sources.json),
and [`data/reference/SPATIAL_DATA_FOUNDATION.md`](../data/reference/SPATIAL_DATA_FOUNDATION.md).
The following are evidence leads or local records, not automatically accepted
assessment inputs:

| Local record | Recorded scope/status | Required before use in a Kochi risk assessment |
|---|---|---|
| `data/raw/rainfall_manual_hr_kerala-sw_kl_1991_2020.csv` | NWDP catalogue metadata is recorded; local observations cover 2000–2014, not the filename’s full declared period. Irregular intervals and no flood labels are documented. | Provider-confirmed coverage, station identity/location/CRS, timestamp/timezone, sampling schedule, quality flags, and a defensible link to the study area and target. |
| `data/raw/kerala.csv` | CWC is the agency in the file; the matching NWDP resource is described as probable but not checksum-matched. Duplicate station-time groups include conflicts. | Confirmed source identity and station metadata; investigate conflicts without silently deduplicating; quality flags, exact coverage, and time/location-compatible outcomes. |
| `data/raw/rwl_manual_hr_kerala_sw_031_2021_2025.csv` and `data/raw/rwl_tel_hr_kerala_sw_031_2021_2025.csv` | NWDP-related records with unresolved gauge reference/datum and some metadata inconsistencies documented in the source register. | Provider-confirmed station identity, gauge zero/datum, location/CRS, units, timestamp/timezone, and official stage/action thresholds. |
| `data/raw/jrc_glofas_rp100_ID185_N20_E70_depth.tif` and `data/raw/jrc_glofas_rp100_ID186_N10_E70_depth.tif` | JRC/Copernicus GloFAS v2.1.2 RP100 modeled depth tiles, WGS84, approximately 90 m, metres; documented as CC BY 4.0 with attribution. These are modeled scenario layers, not observations or a current forecast. | Confirm study-area coverage and model caveats, NoData/water-mask treatment, scenario meaning, and a validated boundary/asset geometry before any exposure claim. |
| `data/raw/ksdma_flood_return_probability_historical_10_25_50.zip` | Acquisition is documented, but the spatial foundation records unresolved reuse terms and raster units/pixel/NoData interpretation. | KSDMA confirmation of permission, bands/units, NoData, method, return-period meaning, and CRS/coverage. |
| `data/raw/nihfw_national_hospital_directory.csv` | NIHFW directory is available, but its coordinate order/CRS and record-level location quality are unresolved; the coordinate review is explicitly not accepted as a point layer. | NIHFW confirmation or a dated, licensed, independently checked hospital GIS source with coordinate order, CRS/datum, positional quality, stable facility identity, and current status. |
| `data/reference/kochi_corporation_boundary.geojson` and `data/raw/koch_wards_2022.geojson` | Boundary is provisional and has a topology issue; ward data is a partial contextual snapshot. Both have documented validation/currency limitations. | A current authoritative boundary/ward source, geometry validation, CRS and positional metadata, publication date, and reuse terms. |

Required additions include authoritative, dated rainfall/forecast sources;
river observations with verified gauge references; local drainage and waterbody
geometry; current geocoded roads, hospitals, shelters, and industrial facilities;
privacy-preserving population exposure data; terrain/hydrology context; verified
historical event footprints and impact records; and asset/service vulnerability
and continuity information. Each dataset must retain source URL, retrieval and
publication dates, coverage, resolution, CRS, units, licence, missingness, and
quality limitations. Do not collect unnecessary personal information.

The local historical rainfall benchmark is a separate measurement benchmark.
It is not a flood model and is not connected to this decision assessment.
Software tests establish code behavior only; they do not establish disaster
prediction validity.

## Known limitations and next milestone

- The evidence matrix describes readiness and gaps; it does not calculate
  confidence or data-quality scores.
- Source availability is not equivalent to provenance verification or
  suitability. Existing observations and map layers are not automatically
  spatially or temporally joined to the intake.
- The recommendations are qualitative, unranked candidates. They do not assign
  responsible authorities unless supported by a local source, estimate costs,
  or quantify intervention benefits.
- No historical event validation of disaster risk is possible in this workflow
  because it does not emit a risk prediction and no compatible local
  event-impact target is currently established.
- A comparison of existing risk platforms and a claim of research novelty have
  not been completed in this phase.

The next data milestone is to resolve the documented KSDMA raster and NIHFW
hospital-coordinate questions, obtain current authoritative drainage/road and
facility layers, and establish verified event-impact records. Then build and
test ingestion/quality gates and an explicitly spatial hazard-exposure analysis
before considering a calibrated risk model.

## Validation record (2026-11-01)

- `.venv\Scripts\python.exe -m pytest -q test_decision_workflow.py` — **25
  passed**.
- Streamlit `AppTest` of `app.py`, including submission of the default intake —
  **0 application exceptions**; the decision page and its report tables
  rendered.
- `.venv\Scripts\python.exe -m pytest -q` — **132 passed, 5 failed, 8
  subtests passed**. The five failures are pinned SHA-256 mismatches for the
  bundled flood-model rows, Kochi boundary (two tests), ward snapshot, and
  NIHFW hospital source. The same five provenance/hash failures were present in
  the pre-change baseline (123 passed); these source snapshots and sidecars were
  not modified as part of this workflow change.

Passing software tests do not validate the scientific accuracy of a risk
prediction. This workflow does not emit a risk prediction.
