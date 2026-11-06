# Intervention-effectiveness evidence sources and data gap

This inventory distinguishes sources that measure hazard impacts from sources
that measure intervention assignment and outcomes. Neither type alone is enough
to train a model that estimates which precaution reduces damage most.

## Candidate evidence

| Source | What it contributes | Why it is not yet a training table for damage reduction |
| --- | --- | --- |
| [J-PAL: Disseminating Flood Warnings to Increase Disaster Preparedness in India](https://www.povertyactionlab.org/evaluation/disseminating-flood-warnings-increase-disaster-preparedness-india) | Randomized evaluation across 319 Bihar panchayats comparing community-volunteer dissemination with smartphone alerts only. The page reports 2022 alert-receipt outcomes and describes longer-run household health/economic outcome follow-up. | The public project page is not a row-level intervention/damage dataset. Its currently reported outcomes mainly concern alert reach and timeliness; it says longer-run impacts are under evaluation. Useful candidate for a future warning-delivery effectiveness study, not immediate training for avoided flood damage. |
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
- site and event identifiers to handle repeated observations and clustered
  uncertainty;
- source ownership, collection methods, definitions, missingness and known bias.

Where an intervention is deployed only at the highest-risk sites, simple
treated-versus-untreated comparisons will be confounded by indication. Prefer
randomized or credible quasi-experimental evaluations when available. If only
aggregate literature estimates exist, show them as sourced evidence ranges or
scenario assumptions, not as observations that train this ML model.

## Current decision

No source above is automatically imported as intervention training data.
J-PAL/IDinsight and government records are candidate evidence to investigate
with data owners; FLODIS is a complementary damage-outcome source. The trainer
remains blocked until a provenance-verified, compatible episode table exists.
