# AI_RESILIENCE scientific model design

**Version:** 0.1 — research plan, not a validated operational model  
**Scope:** Kochi/Ernakulam flood resilience and compound-hazard decision support

## 1. Separate the scientific questions

The application must not collapse different hazards into one uncalibrated "disaster probability".

### Track A — river/catchment flood events

Potential outcome source: INDOFLOODS gauge-event records, which contain gauge IDs, event start/end dates, peak levels, event durations and associated gauge metadata. The public metadata preview includes Kerala gauges, including Ramamangalam on the Muvattupuzha river, but does not show an exact "Ernakulam" district label. This is a candidate regional hydrology source, not proof of Kochi-wide flood labels.

Before modeling:
- Audit the complete station list, event counts and gauge-to-catchment coverage.
- Verify gauge warning/danger levels, units, reference datum, source period and event construction.
- Confirm whether the event and rainfall files have matching IDs and what the precipitation windows mean.
- Do not treat absent event rows as non-floods.
- Do not match INDOFLOODS to NWDP observations by station name alone. A verified identifier crosswalk and temporal overlap are required.
- Keep events grouped by gauge/event and hold out later years or whole events for evaluation.

### Track B — urban/pluvial flooding in Kochi

River gauge events alone do not label road/ward waterlogging. An urban flooding model needs spatially and temporally defined outcomes such as verified inundation-depth points/polygons, documented road closures/waterlogging reports, or authoritative ward-level impact records. Candidate inputs include rainfall intensity/accumulation, elevation/slope, impervious cover, drainage and canal capacity/condition, tidal/backwater conditions where relevant, and exposure. Every feature needs provenance, spatial resolution, timestamp and licence.

Until urban flood outcome data are obtained and validated, show transparent **susceptibility/exposure indicators** and scenario comparisons, not a learned ward-level probability.

### Track C — cyclone + flood compound scenarios

Treat this as a scenario-analysis layer until joint event outcomes and compatible data are available. Record each scenario's assumptions, source, units, time window and uncertainty. Do not multiply independent probabilities or present scenario scores as calibrated likelihoods without a justified joint model and evaluation.

## 2. Proposed target definition before feature engineering

For a candidate river-gauge model, pre-register a target such as:

"At gauge g and issue time t, predict whether a verified threshold-exceedance event begins within the next H hours."

This is only a template. The final H, event definition, threshold source and whether the event table records all threshold exceedances must be decided from the dataset paper and station documentation before training. Event start time and the target threshold must be verified independently.

Potential predictors must be known at issue time:
- antecedent observed rainfall accumulated only up to t;
- archived rainfall forecasts whose issue time is at or before t and whose valid times cover the future horizon;
- recent river-level history only if station identity, datum, sampling and publication time are verified;
- catchment descriptors that are static and properly linked to the gauge.

Do not use peak flood level, event duration, event-scale rainfall windows that include future rainfall, event end time, or any post-event report as predictors for an early-warning target.

## 3. Build the dataset in auditable stages

1. **Raw:** download original source bytes, keep them immutable, record URL, publisher, retrieval timestamp, SHA-256, declared licence and source version.
2. **Audited:** validate schema, time coverage, units, missingness, duplicate/conflicting keys, station coordinates and identifiers. Investigate conflicts rather than silently averaging.
3. **Crosswalked:** join only through explicit IDs or independently verified station matching; store match evidence and confidence.
4. **Labelled:** create a versioned outcome table with target definition, spatial unit, time interval, event ID, evidence source and reviewer. Keep uncertain/ambiguous labels separate.
5. **Feature-ready:** freeze issue time/horizon and enforce as-of joins so future information cannot leak into predictors.
6. **Evaluation-ready:** group by event/gauge and preserve a final chronological holdout that is not used for tuning.

No stage should silently overwrite or "repair" the original data.

## 4. Baselines and evaluation

Start with simple, interpretable baselines before trying complex machine learning:
- climatology/event-rate baseline where valid;
- persistence or threshold baseline only when threshold data are verified and available at issue time;
- a regularized logistic model or shallow tree as an interpretable candidate, if sample size supports it.

Report:
- number of gauges, independent events, non-event windows and years;
- missingness and class balance;
- precision, recall, F1 and confusion matrix at a predeclared operating threshold;
- precision-recall AUC for imbalanced binary targets, if enough independent examples exist;
- Brier score/reliability plots only when there are enough independent outcomes to assess calibration;
- uncertainty intervals and performance by held-out event/year/gauge where feasible.

Use event-grouped and chronological evaluation to prevent adjacent windows from the same flood entering both train and test. Do not use a random row split as the only evidence. Compare against the baseline and keep the final holdout untouched.

## 5. Model release gates

| Gate | Required evidence | If not met |
|---|---|---|
| G0 — Source integrity | Provenance, licence, checksums, schema and units reviewed | Keep source as unvalidated |
| G1 — Spatial/temporal validity | Verified gauge/catchment crosswalk and time conventions | No joins or spatial claims |
| G2 — Outcome validity | Clear event target and independently supported non-event periods | No classifier training |
| G3 — Leakage control | Issue time/horizon fixed; every feature available by issue time | Reject dataset build |
| G4 — Evaluation | Event/time holdout, baseline, metrics, sample/event counts and uncertainty | No predictive claim |
| G5 — Operational safety | Independent review, monitoring, limitations and authority escalation | Exhibition/research use only |

## Current decision

The model is **not ready for operational flood prediction**. INDOFLOODS is registered for reproducible acquisition and descriptive audit; local station coverage and event/non-event suitability must be quantified. Kochi urban flooding needs separate outcome evidence. The exhibition can still demonstrate evidence-backed historical hydrology, source quality, map-based exposure and clearly hypothetical scenarios while these gates remain visible.
