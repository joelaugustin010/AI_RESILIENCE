# Kochi Cyclone + Flood Resilience — Integrated Milestone

**Branch:** `milestone/kochi-cyclone-flood-resilience-20261102`  
**Status:** implementation in progress; research prototype only  
**Scope:** one integrated milestone covering rainfall, river flooding, cyclone exposure, compound interactions, service consequences and decision support.

## Objective

Deliver one coherent Kochi-focused workspace that connects flood and cyclone evidence and explains how combined conditions can affect critical services. The milestone is not complete merely because a rainfall or event-severity model trains. Every model must pass source, timing, geographic, label and held-out evaluation checks before it can influence a predictive claim.

## Integrated architecture

1. **Evidence foundation**
   - Preserve source URL, publisher, retrieval time, licence/reuse note, checksum, units, timezone, spatial and temporal coverage, quality flags and limitations.
   - Keep historical observations, archived forecasts, official warnings and hypothetical scenario inputs distinct.
   - Do not join gauges or facilities by name alone.

2. **Rainfall and flood**
   - Include the leakage-aware next-day rainfall research baseline and explicit promotion gate: the model must beat both persistence and training-monthly-median baselines on untouched chronological test MAE.
   - Rainfall prediction is a supporting weather component, not a flood prediction.
   - River-level values require station identity, timestamp, units, gauge datum and source-defined warning/danger references.
   - Flood outcomes require independently verified event/location/time labels and monitored non-event periods.
   - INDOFLOODS event-only severity results are exploratory and not eligible for live integration. The current baseline is weak and does not predict flood occurrence.

3. **Cyclone**
   - Use IMD/RSMC best-track data for historical storm-track context.
   - Preserve suspect-position and suspect-date flags.
   - Track-to-Kochi-point distance is only a screening statistic, not a wind footprint, surge extent or local impact probability.
   - Operational forecast inputs must preserve bulletin issue time, valid time, forecast lead, product definition and source.

4. **Compound cyclone + flood**
   - Align cyclone track/intensity, rainfall, river level, tide/coastal water, drainage/outfall and independently verified impacts on a common timeline.
   - Check whether rainfall, river response and coastal backwater conditions overlap in the same catchment and event.
   - Examine cascading dependencies across hospitals, roads/bridges, electricity, drinking water, communications, shelters, schools, drainage and industrial facilities.
   - If evidence is missing, show the gap; do not synthesize a probability, depth, damage or casualty count.

5. **Decision support**
   - Explain pathways and possible consequences.
   - Provide before/during/after preparedness checklists.
   - Identify evidence needed for a location-specific assessment.
   - Direct real-world safety decisions to official IMD, CWC, KSDMA and local-authority instructions.

## Implemented in this milestone branch

- A reusable evidence-aware scenario assessment engine in `src/compound_hazard_assessment.py`.
- The baseline-gated next-day rainfall research model and feature-day selector, carried into this milestone so rainfall research is evaluated in the same CI run.
- A redesigned Cyclone + Flood workspace in `app_pages/compound_scenario.py` with:
  - hypothetical, historical, current-observation and official-forecast evidence types;
  - explicit observation time and source reference;
  - optional rainfall, river-level, cyclone-distance and wind inputs;
  - reference comparisons only when both observation and reference threshold are supplied;
  - compound consequence pathways for selected critical services;
  - before/during/after actions, data gaps and downloadable JSON review.
- Automated tests covering compound pathways, threshold safeguards, negative/invalid inputs, date ordering and the no-probability boundary.

## Scientific acceptance gates

A numerical flood/cyclone prediction may be considered only when all applicable gates pass:

- **Governance:** licence and reuse conditions confirmed; only eligible data included.
- **Timing:** prediction issue time and horizon fixed; no feature observed after issue time.
- **Geography:** station/catchment/facility identity and spatial relationship independently verified.
- **Labels:** positive and negative/background periods have explicit, independently sourced definitions; missing reports are not treated as non-events.
- **Evaluation:** chronological holdout plus event/storm grouping; compare with persistence/threshold baselines; report sample counts, class balance, precision, recall, F1, confusion matrix and uncertainty.
- **External review:** local relevance and limitations reviewed before any live assessment integration.

Passing unit tests proves software behavior, not scientific validity.

## Current known blockers

- Flood records do not yet provide a validated Kochi event/non-event time series linked to local rainfall and river gauges.
- Existing INDOFLOODS severity baseline is event-only, generic across gauges, weak on held-out gauges and not a flood-occurrence model.
- Local CWC/NWDP rainfall and river-level station-time conflicts, gauge datum, timezone and station crosswalk questions remain.
- Cyclone best-track archive provides historical track context, not local wind/surge/flood impact labels; underlying IMD reuse terms need confirmation.
- Verified tide, surge, drainage/outfall, elevation and ward/facility exposure layers are still needed for local impact quantification.

## Milestone completion checklist

- [x] Integrated cyclone + flood workspace and transparent scenario engine.
- [x] Critical-service consequence pathways and preparedness actions.
- [x] No fabricated probability, damage or casualty output.
- [x] Automated unit tests for the scenario engine.
- [x] Leakage-aware rainfall research baseline and baseline-promotion gate included in this milestone.
- [x] Privacy- and feature-timing-safe INDOFLOODS exploratory baseline included with explicit weak-skill decision.
- [x] Clean-checkout CI passes on the milestone pull request (run 41430136503).
- [ ] Rainfall model-training report and baseline comparison reviewed.
- [x] Flood baseline re-run and report reviewed; weak results remain research-only (artifact generated in run 41430136503).
- [x] Cyclone best-track audit artifact generated in CI (run 41430136503).
- [ ] Source and spatial review for Kochi/Ernakulam gauges and cyclone evidence documented.
- [ ] Rainfall research model evaluated against simple baselines and reviewed for local relevance.
- [ ] Flood prediction gate remains blocked until valid event/non-event data are available.
- [ ] Final integrated review and deployment smoke test.

**Release rule:** keep the new workspace clearly labelled as scenario/research support until all remaining scientific and deployment gates are documented. Do not merge weak experimental classifiers into the live assessment.
