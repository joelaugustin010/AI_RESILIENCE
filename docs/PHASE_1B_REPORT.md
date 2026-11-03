# AI_RESILIENCE Phase 1B: scientific intelligence and repository integrity

**Review date:** 2026-11-01
**Scope:** Existing decision workflow, evidence quality, uncertainty, compound hazards,
infrastructure dependencies, recommendation readiness, and historical-validation readiness.

## Git integrity report

No synchronization was attempted. The following findings use the local
`origin/main` tracking ref available at review time; no network fetch was
performed, so this is not a claim about the live remote after that ref was
updated.

- Worktree branch: `main`, at `3ae5f0650f098db08773c15b1414087e90cdf337`.
- Tracking ref: `origin/main` at `be4bccda64e928dbd221275ade21745da21ff888`.
- Merge base: `3ef79470ce5719fb2033a5138c4529fb6b627511`.
- `HEAD...origin/main`: two local-only commits and 219 remote-tracking-only
  commits. The local-only commits are `8621298` (“Integrate Eloor air quality
  analysis”, 2026-10-25) and `3ae5f06` (a merge whose second parent is the
  then-current `origin/main` at `3ef7947`). `origin/main` subsequently advanced
  through the commits ending at `be4bccd` (2026-10-31).
- This graph indicates ordinary divergence after an October 25 merge; the
  available ancestry does not indicate a force-push or rewritten shared
  history. The 219 count includes all commits on the newer remote-tracking
  history, not 219 independent feature branches.
- Other local branches and linked worktrees exist. Commit authorship can
  identify recorded commit authors, but it cannot establish ownership of
  uncommitted files.

At the start of this phase, the worktree already contained edits to
`app_pages/decision_workflow.py`, `assessment.py`, `src/decision_workflow.py`,
`src/flood_risk.py`, and `test_decision_workflow.py`, plus untracked work under
`AI_RESILIENCE/`, `data/`, `docs/`, `scripts/`, and `requirements-data.txt`.
The nested `AI_RESILIENCE/` directory contains its own `.git`; the untracked
browser-profile tree contains application/profile artifacts. Their ownership
cannot be inferred safely. They were not staged, deleted, moved, or otherwise
altered. The pre-existing one-blank-line EOF changes in `assessment.py` and
`src/flood_risk.py` were preserved.

**Safe synchronization strategy:** First confirm ownership and intended
disposition of uncommitted and untracked work. After approval, fetch the remote
without changing the worktree, create a new worktree from the then-current
`origin/main`, and transplant only reviewed, owned changes. Compare the Eloor
commit with the newly fetched history before replaying it because equivalent
work may already have landed. Do not merge the old two-commit local tip or
rebase shared branches as a shortcut. No reset, force-push, merge, or rebase
was performed in this phase.

A separate available tracking ref,
`origin/fix/cross-platform-hash-tests-readme-20261031`, was inspected. Its
`.gitattributes` contains the same four LF rules used here plus rules for
additional processed datasets; that ref was not merged or cherry-picked, and
its existence does not establish that the changes are present in `origin/main`.

## Phase 1 re-audit and test-count reconciliation

The existing multi-page Streamlit application and Decision Workflow were
retained. The previous workflow already had scenario intake, qualitative
comparisons, evidence inventory, user-entered action costs and priorities,
budget arithmetic, and CSV/HTML export. This phase extends those surfaces
rather than replacing them.

The repository `HEAD` version of `test_decision_workflow.py` contained 16
test methods. The Phase 1 working version before Phase 1B contained 25 methods.
Phase 1B adds focused tests in separate evidence, dependency, validation, and
Streamlit integration modules. Repository history contains other historical
workflow revisions with different method counts (including 27, 31, and 34);
the cited “29 tests” could not be tied to the current branch or a specific
revision. No tests were removed to reconcile counts.

The current connected page preserves the original workflow and export fields;
the exported report now additionally records evidence states, uncertainty
categories, conceptual infrastructure links, recommendation candidates, and
the recommendation prioritization gate.

## Evidence-quality engine

`src/evidence_quality.py` defines seven categorical states: **Verified**,
**Provisionally verified**, **Unverified**, **Outdated**, **Incomplete**,
**Conflicting**, and **Unavailable**. State selection is rule-based and
qualitative; there is no weighted quality score. A publisher's government
status alone cannot produce “Verified.” Source identity, dates, reuse terms,
geographic and temporal fit, measurement quality, spatial characteristics,
completeness, and verification notes are carried for each listed workflow
record.

The Decision Workflow evidence inventory now includes those fields for its
configured hydrology, example, boundary, ward, hospital, JRC, and KSDMA records.
For locally pinned snapshots it also compares the file bytes with the
documented SHA-256. A mismatch downgrades provenance to unverified rather than
silently changing the expected hash. The current source limitations remain:

- CWC rainfall has documented conflicting station-time groups; original
  readings are not averaged or deduplicated.
- The manual rainfall record is historical, has incomplete temporal coverage
  relative to its filename, and is only used by the separate rainfall
  measurement benchmark.
- River levels have unresolved gauge-reference/metadata issues; no threshold
  comparison is made.
- The JRC RP100 layer is modeled scenario evidence, not an observation or
  forecast; transparent/NoData pixels do not imply safety.
- The KSDMA archive's pixel meaning, NoData semantics, and reuse permission
  remain unresolved.
- NIHFW hospital coordinates and community boundary/ward layers are not
  accepted as verified exposure geometries.

States describe evidence handling for this prototype. They do not prove that a
source is scientifically suitable for every question or that all source
records are exhaustive.

## Uncertainty and conclusion controls

`src/uncertainty.py` reports measurement, data-quality, spatial, temporal,
model, and scenario uncertainty separately. Each category has an explicit
downstream consequence and a resolution step. Missing data remain unknown;
they are not interpreted as zero hazard, zero exposure, or zero risk. No
confidence percentage is generated.

The connected assessment continues to return “Insufficient evidence for a
reliable numerical prediction” and never assigns low/elevated/high risk. A
source mismatch or missing spatial link therefore cannot create a
success-shaped “safe” result.

## Compound-event and infrastructure dependency framework

`src/infrastructure_dependencies.py` represents potential pathways as
directed edges with a relationship type, evidence state, and optional source
reference. The conceptual graph distinguishes:

- a **possible causal meteorological driver** (cyclone conditions and heavy
  rainfall), which still requires event-specific attribution;
- **conditional hydrologic processes** (rainfall, river level, drainage
  impairment, and urban flooding);
- **service dependencies** (road passability, emergency access, hospital
  continuity, electricity, and water); and
- **spatial overlap** (flood extent and population exposure).

Every supplied Kochi-specific link is currently **Unverified** and has no
local evidence reference. Path tracing reports an unresolved dependency if
any edge is unverified or lacks a source. The UI explicitly labels this graph
as conceptual. A possible cascade such as flood → road passability → emergency
access → hospital continuity is a hypothesis to investigate, not an assertion
that a road or hospital is actually vulnerable.

This representation does not estimate event co-occurrence, conditional
probability, failure propagation, or service loss. Spatial/temporal overlap
and dependency topology must be evidenced before an interaction is quantified.

## Recommendation prioritization

The existing candidate generator now includes the assessment trigger,
qualitative rationale, and required evidence/authority. Candidates remain
unranked. `recommendation_priority_readiness` requires a verified, sourced,
unit/scale-defined record for expected risk reduction, affected population,
infrastructure importance, feasibility, cost, implementation time, and
uncertainty. For benefits it distinguishes **Validated estimate** from
**Demonstrated benefit**; an unsupported “estimated” value is not accepted.

Passing the evidence gate still does not create a rank: transparent comparable
scales and policy weights require stakeholder and authority decisions. No
weights, costs, intervention benefits, or local prioritization results were
invented.

## Historical-event validation readiness

`src/historical_validation.py` provides a fail-closed readiness check requiring
independently reviewed outcomes, source URLs, label definition, event period,
feature cutoff and horizon, independently reviewed geographic and temporal
matching, dataset hash, code/method version, and predeclared split assignment.
It rejects feature cutoffs at or after the outcome window and incomparable
timezones.

The metric helper reports held-out confusion counts, precision, recall,
specificity, F1, accuracy, and the case IDs for false positives and false
negatives. Undefined denominators remain null. These functions are tools for
future evaluation; no risk model or event-impact evaluation was performed.
The framework and data gates are documented in
[`DECISION_WORKFLOW.md`](DECISION_WORKFLOW.md).

## Platform and research comparison

This is a scoped desk review of primary platform descriptions and one
peer-reviewed review citation, not a systematic literature review.

| Platform / research | Established capability (source) | Scope/limitation relevant to this project |
|---|---|---|
| INFORM Risk / INFORM product suite | Global, open-source crisis/disaster risk assessment; JRC scientific lead; the product suite separates structural risk, warning, severity, and climate-change products. [INFORM overview](https://drmkc.jrc.ec.europa.eu/inform-index) | Global/subnational comparative products and methodologies; not a verified, asset-level Kochi event assessment. Its existence means general multi-dimensional risk indexing is not an originality claim. |
| FEMA Hazus | GIS-based hazard models combine inventory, hazard intensity, and damage functions to estimate physical, economic, and human impacts. [FEMA Hazus](https://www.fema.gov/flood-maps/products-tools/hazus) | A mature, more quantitative impact-modeling approach with US-specific inventories and methods; those baseline inventories/functions cannot be assumed valid for Kochi. |
| InaSAFE | Open-source scenario tool combines hazard and exposure information to support impact scenarios and preparedness. [InaSAFE](https://inasafe.org/) | Demonstrates that scenario overlay and impact-oriented planning are established techniques; local input quality and validated consequences remain essential. |
| NIST Community Resilience Planning Guide | Community planning guidance explicitly covers buildings/infrastructure, dependencies, cascading consequences, and performance goals. [NIST Volume II](https://www.nist.gov/publications/community-resilience-planning-guide-buildings-and-infrastructure-systems-volume-ii) | Establishes that infrastructure dependencies and cascades are not a novel concept. It is planning guidance, not a current Kochi observation network. |
| Zscheischler et al. (2020) | Peer-reviewed review titled “A typology of compound weather and climate events,” *Nature Reviews Earth & Environment*, 1, 333–347. [DOI](https://doi.org/10.1038/s43017-020-0060-z) | Compound weather/climate events are an established research topic; a compound label or dashboard feature alone is not a contribution claim. |
| UNDRR terminology | Defines disaster risk in relation to hazard, exposure, vulnerability, and capacity. [UNDRR Disaster Risk](https://www.undrr.org/terminology/disaster-risk) | Provides a conceptual framing, not a universal numerical formula or validated local coefficients. |

**Defensible contribution statement:** AI_RESILIENCE may contribute a reproducible,
Kochi-focused decision workflow that exposes source and suitability states,
keeps uncertainty and unresolved hazard/service dependencies explicit, and
withholds scores and ranks until local evidence supports them. This is an
engineering and evaluation objective, **not a claim of being first or
scientifically novel**. A systematic search, comparison of peer-reviewed
methods, local stakeholder review, and verified outcome data are still needed
to assess any research contribution.

## Validation and integrity findings

### Tests

The new tests exercise evidence-state transitions and hashes, uncertainty
categories, unresolved and verified dependency paths, recommendation evidence
gates, historical-validation blockers/metrics, the existing workflow, and
Streamlit form submission. Passing software tests do not establish prediction
accuracy or evidence suitability.

Final validation on 2026-11-01:

- Focused workflow, evidence, dependency, historical-validation, and Streamlit
  tests: **46 passed, 7 subtests passed**.
- Full repository suite (`python -m pytest -q`): **158 passed, 15 subtests
  passed**.
- The five previously failing SHA-256 checks now pass without changing
  expected hashes.
- Pylance reported no diagnostics in the new evidence, uncertainty,
  dependency, historical-validation, or test modules. Existing warnings remain
  for the unused `project_root` report parameter and Streamlit cache-key
  parameters.
- `git diff --check` found only the already-present extra blank lines at EOF
  in `assessment.py` and `src/flood_risk.py`; neither file was changed for this
  phase.

### Five pre-existing SHA-256 failures

The earlier failures were reproduced and traced to Windows checkout line-ending
conversion, not incorrect expected source hashes. The committed blobs were LF;
the worktree had CRLF conversions for the boundary (+1 line ending), ward
snapshot (+77), NIHFW directory (+30,274), and flood-example CSV (+6). For each
file, replacing CRLF with LF produced bytes exactly equal to `git show
HEAD:<path>`. The expected hashes were left unchanged.

`.gitattributes` now pins LF for these four hash-verified text snapshots; the
current worktree files were normalized only after byte-for-byte comparison
with their committed blobs. This makes source hashes portable without
rewriting or weakening the tests.

## Limits and next data requirements

No risk model was trained, no probability or risk class was estimated, no local
infrastructure cascade was verified, and no intervention benefit was
quantified. The platform comparison was not systematic. Phase 1B is therefore
an implemented evidence/readiness framework, not a validated disaster-risk
system.

Next data work should obtain:

1. Provider-confirmed CWC/NWDP identity, station metadata, sampling/QC
   information, and resolution of duplicate conflicts.
2. River station identity, gauge datum/zero, coordinate metadata, and official
   stage thresholds.
3. KSDMA confirmation of pixel meaning, NoData, method, return-period
   definition, and reuse permission.
4. Current authoritative Kochi boundaries, roads, drainage, hospitals,
   emergency facilities, utilities, and population summaries, with documented
   CRS, dates, completeness, positional quality, and licences.
5. Time-stamped, independently sourced event extents and impacts, plus
   reviewed spatial/time matching and feature cutoffs.
6. Documented infrastructure operators, dependencies, redundancy, backup
   capacities, and failure/repair records.

Only after these prerequisites and a predeclared validation design should a
Kochi hazard-exposure or cascading-impact model be considered.
