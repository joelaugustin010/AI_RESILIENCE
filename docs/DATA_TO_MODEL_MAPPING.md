# Phase 2 data-to-model mapping

## Analytical guardrails

The existing Decision Workflow remains an evidence-review and action-planning
tool, not a calibrated risk or impact model. The new snapshots inform visible
context only; none is silently joined to the user's location, hospitals,
roads, a flood raster, or a historical impact label.

| Input/evidence | Observable or derived output | Permitted interpretation now | Not supported |
|---|---|---|---|
| NWDP rainfall CSVs | Source rows, date ranges, station counts, duplicates/conflicts | Inspect source measurements and data coverage, preserving conflicts | Fill missing dates, treat conflicts as independent certainty, infer city-wide rainfall, or issue a forecast |
| Manual hourly rainfall source | A one-hour next-record measurement benchmark using exact consecutive pairs and a chronological holdout | Retrospective rainfall-measurement comparison only; its separate benchmark does not feed the hazard assessment | Current rainfall forecast, flood prediction, local Kochi skill, or hazard-impact validation |
| NWDP river-level CSVs | Source levels in reported metres and coverage | Inspect station/time records descriptively | Danger classification, station comparison without gauge datum, flood probability, or river-to-hospital causal claim |
| IMD annual grid | Nearest-cell daily series, range/mean/maximum and coverage | Describe gridded daily rainfall at the cell and display source/time context | Exact assessment-point rainfall, gauge replacement, ward exposure, flood depth, probability, or impacts |
| NASA POWER | Fixed-point daily precipitation/temperature/wind series and missing-value counts | Broad meteorological context from a gridded/model product | Local observation, cyclone attribution, source attribution, flood threshold, or forecast |
| JRC GloFAS RP100 | Existing return-period flood-depth scenario layer | Explain as modelled river-flood scenario context with NoData caveat | Observed flood extent, event probability for a specific site, validated hospital exposure, or safe/unsafe classification |
| KSDMA archive | Existing unverified raster/ZIP | Keep source and interpretation unresolved in inventory | Any model overlay, pixel-derived score, or exposure statement |
| OSM road snapshot | Count of mapped highway-tagged ways in the captured rectangle | Report source extent and snapshot timestamp | Routing, road condition/passability, emergency access, flood interruption, or hospital connectivity |
| USGS earthquake query | Query bounds/date/minimum magnitude and returned feature count | State the exact catalog query result | Zero local hazard, complete seismicity, earthquake probability, or building vulnerability |
| NIHFW/hospital and population/utility gaps | Inventory of missing or unverified inputs | Mark unavailable and identify acquisition need | Spatial exposure, service coverage, population-weighted impacts, or cascade claims |
| KSPCB air records and industrial documents | Dated source records and monitoring-network context | Display sourced measurements only where their units/time/provenance are explicit | Factory attribution, emissions ranking, cause, or industrial vulnerability from proximity/AQI alone |

## Distinguishing evidence types

1. **Observed/source-reported data:** preserved station measurements or
   authoritative records, subject to provider QA and unresolved metadata.
2. **Derived measurements:** nearest IMD cell extraction, parsed quality
   summaries, daily statistics, and record counts. Inputs and operations are
   reproducible and labeled.
3. **Model estimates/scenarios:** NASA POWER gridded products and JRC RP100
   model scenario are labeled as such. Their outputs are not observations.
4. **Missing evidence:** absent, inaccessible, unlicensed, incomplete, or
   spatially unvalidated data are marked unavailable/uncertain, never zero.
5. **Uncertainty:** measurement, data-quality, spatial, temporal, model, and
   scenario uncertainty remain distinct in the Phase 1B uncertainty register.
6. **Unsupported conclusions:** no local hazard ranking, probability,
   facility vulnerability, compound-hazard score, source attribution,
   intervention benefit, or predictive accuracy is emitted from these files.

## Compound hazard and dependency handling

Heavy rainfall, cyclone conditions, river changes, drainage performance,
urban inundation, and service disruption are represented as possible causal
or conditional pathways in the existing dependency framework, not as additive
risk scores. The newly acquired datasets do not provide matched event timing,
drainage state, coastal water, flood outcome, and service impacts sufficient to
quantify those interactions.

The OSM road layer is not connected to the unverified hospital directory;
neither is joined to a verified flood extent. A possible sequence such as
flooding -> road passability -> emergency access -> hospital continuity stays
an unresolved dependency. The app does not state that an actual facility is
exposed or inaccessible.

## Recommendations

Existing recommendations remain unranked unless comparable verified evidence
is available for expected risk reduction, population affected, infrastructure
importance, feasibility, cost, implementation time, and uncertainty.
Demonstrated benefits are distinct from estimated benefits. These Phase 2
snapshots do not supply those records and therefore do not create an
intervention score or rank.

## Historical validation

No acquired snapshot has an independently reviewed matched outcome. Before
validation, define event identity, outcome source, spatial and time matching,
feature cutoff/horizon, false-positive/negative review, reproducibility,
predeclared splits, and evaluation metrics. The existing validation-readiness
code is not evidence that a predictor is accurate. The retrospective
one-hour manual-rainfall measurement benchmark is documented separately in
`PHASE_4_VALIDATION_REPORT.md`; it does not validate any disaster-impact
model.
