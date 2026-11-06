# Intervention-effectiveness evidence sources and data gap

This inventory distinguishes sources that measure hazard impacts from sources
that measure intervention assignment and outcomes. Neither type alone is enough
to train a model that estimates which precaution reduces damage most.

## Candidate evidence

| Source | What it contributes | Why it is not yet a training table for damage reduction |
| --- | --- | --- |
| [Yale / Inclusion Economics: Community Messengers Turn Flood Forecasts into Protection (September 2026)](https://ie.yale.edu/research/community-messengers-turn-flood-forecasts-protection) | Four-year randomized trial (2022–2025) across 319 North Bihar panchayats: 160 assigned trained community messengers and 159 relied on existing channels; 5,582 households followed over four monsoons, with satellite-measured village flood severity. The public policy brief reports outcomes including home flooding, house damage, food insecurity and borrowing. | This is the strongest identified candidate for a first real intervention-effect study, specifically the bundled intervention "community warning dissemination". The public brief provides aggregate estimates, not the household/panchayat-level microdata needed to train a contextual ML model. Data access, codebook, cluster identifiers, treatment assignment, panel structure, survey weights and consent/usage terms must be requested from the research team before use. Bihar trial effects must not be assumed to transfer to Kochi. |
| [IDinsight: Impact of a flood forecasting tool in Bihar](https://www.idinsight.org/project/the-impact-of-a-flood-forecasting-tool-on-socioeconomic-outcomes-in-bihar-india/) | Reports evaluation findings on preparedness, health costs and household economic coping associated with flood warnings. | Public summary statistics do not supply the linked episode-level treatment, baseline covariates and comparable damage outcomes required by the current trainer. Raw-data access and definitions would need to be confirmed. |
| [FLODIS open flood-impact dataset](https://www.nature.com/articles/s41597-023-02376-9) | Links remotely observed flood footprints to displacement, fatalities and economic-damage records; reports 335 displacement events and 695 mortality/damage events for 2000–2018. | It is an impact/outcome source, not a verified intervention-assignment register. It cannot by itself identify which precaution caused lower damage. |
| [CWC assessment of flood-affected and protected areas in India](https://www.pib.gov.in/Pressreleaseshare.aspx?PRID=2037094&lang=1&reg=3) | Government-reported district-scale flood area and area protected by structural measures over 1986–2022. | Aggregated protected/affected area is not a matched site-event panel with intervention timing, exposure and damage outcomes. It is useful for contextual evidence and validation questions, not direct causal training as-is. |
| [World Bank IEG evaluation of disaster-risk-reduction activities](https://ieg.worldbankgroup.org/evaluations/reducing-disaster-risks-natural-hazards/chapter-4-effectiveness-world-banks-disaster) | Explains the scarcity and inconsistency of outcome-level measurement in DRR portfolios; many indicators measure project outputs rather than reduced risk or loss. | Confirms a structural evidence gap: project completion/output records must not be mislabelled as measured damage reduction. |

## Minimum data collection target

For each stable action ID and hazard, collect comparable site-time episodes with:

- action implementation status, start time, quality/fidelity and coverage;
- a comparable no-action or alternative-action group;
- pre-intervention hazard intensity, forecast lead time, exposure, vulnerability,
  asset type, socioeconomic context and baseline condition;
- measured post-event damage outcomes with units, spatial scope and outcome window;
- unique observation IDs (for example, household-season) plus site/cluster and
  event identifiers to handle repeated observations and clustered uncertainty.
  For cluster-randomized studies, `site_id` must be the assignment cluster
  (for example, panchayat), while `episode_id` identifies each household-season;
- source ownership, collection methods, definitions, missingness and known bias.

Where an intervention is deployed only at the highest-risk sites, simple
treated-versus-untreated comparisons will be confounded by indication. Prefer
randomized or credible quasi-experimental evaluations when available. If only
aggregate literature estimates exist, show them as sourced evidence ranges or
scenario assumptions, not as observations that train this ML model.

## Current decision

No source above is automatically imported as intervention training data.
The 2026 Bihar randomized trial is a concrete candidate for a first flood
warning-dissemination model, but only after authorized microdata access and
compatibility review. It evaluates a bundled community-messenger intervention;
it cannot isolate the causal contribution of individual household actions
such as sandbagging or drainage clearing. FLODIS is a complementary
damage-outcome source, not a substitute for treatment assignment. The trainer
remains blocked until a provenance-verified, compatible episode table exists.
