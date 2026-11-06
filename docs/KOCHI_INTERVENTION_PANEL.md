# Kochi intervention panel: data contract and audit

This is the first executable data pathway for evaluating physical flood-mitigation work in Kochi (including, but not automatically limited to, Operation Breakthrough).

## Unit of observation

One row = one site during one independently documented flood event. A site may appear in multiple events. Each intervention version must be evaluated separately. The treatment indicator is time-varying: a site/event is treated only when the intervention was operational before that event. Events before completion are pre-implementation observations.

## Required columns

- `observation_id`: unique source-linked observation key.
- `site_id`: stable ward, drainage catchment, canal reach or asset-area identifier.
- `event_id`, `event_date`: independently defined flood event and date.
- `intervention_id`, `implementation_date`: exact intervention version and verified operational/completion date.
- `treated`: 1 only when the intervention was operational for that site/event; otherwise 0.
- `outcome_name`, `outcome_value`, `outcome_unit`: one consistently measured outcome (e.g. inundation depth in cm, duration in hours, or damage cost in INR). Do not mix outcomes or units.
- `rainfall_mm`: event/site rainfall observation with a traceable source.
- `tide_level_m` and `river_level_m`: strongly recommended where relevant.
- `source_id`, `source_url`: record-level provenance, not merely a general homepage.

Keep extra pre-event covariates in separate columns with documented definitions and measurement times. Never include post-intervention or post-event variables as adjustment features.

## Run the audit

```powershell
python scripts\audit_kochi_intervention_panel.py --data data\local\kochi_intervention_panel.csv
```

The input CSV is intentionally not populated with example measurements. The template at `data/templates/kochi_intervention_panel_template.csv` contains only its header. Do not put restricted household records in Git.

## Readiness gate

The audit checks schema, dates, duplicate site/event rows, binary treatment, consistent outcome and intervention definitions, source references, treated/comparison site counts, and basic pre/post coverage. A passing result means **ready for design review only**. It does not prove parallel trends, no spillovers, valid comparison sites, or causal identification, and it does not train a model.

The next stage requires a human review of treatment targeting, concurrent projects, exposure changes, rainfall/tide/river confounding, outcome comparability, missingness, and multiple pre-intervention event trends. Only after that review should an appropriate panel estimator be implemented. The existing episode-level CATE learner must not be fed this panel by simply reshaping rows; the estimand and dependence structure differ.

## Current Kochi evidence status

Operation Breakthrough and related Kochi drainage works are documented intervention leads. Public summaries currently do not provide a complete linked site-by-event outcome panel. Project work orders, geospatial footprints, completion/operational dates, maintenance history, event rainfall/tide/river levels, inundation measurements and comparable untreated/not-yet-treated locations remain necessary. No intervention effect is asserted by this scaffold.
