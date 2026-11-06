# Intervention-effectiveness evidence sources and data gap

This inventory distinguishes sources that measure hazard impacts from sources
that measure intervention assignment and outcomes. Neither type alone is enough
to train a model that estimates which precaution reduces damage most.

## Candidate evidence

| Source | What it contains | ML suitability and limitations |
| --- | --- | --- |
| [WFP / World Bank: Bangladesh Forecast-Based Anticipatory Action Impact Evaluation 2024](https://microdata.worldbank.org/catalog/8009) ([IHSN metadata and dictionary](https://catalog.ihsn.org/catalog/13493/data-dictionary)) | **Highest-priority empirical source.** Three-arm randomized timing of electronic cash transfers around the July 2024 Jamuna-basin flood. Three survey rounds; Round 1 has 9,165 household records, Round 2 7,337, Round 3 4,913. The catalog lists a Round 3 asset-ownership-and-damage file (103,422 asset rows), administrative data (11,810 rows), GIS with buffers (96,082 rows), and a randomization file (71,143 rows). Asset damage is explicitly asked as damage due to floods since 15 June 2024; the survey also records transfer receipt/timing and household coping/welfare outcomes. | **Best located real intervention + outcome combination.** The randomized treatment is timing of cash assistance (earlier before flood peak versus later arms), not physical precautions such as embankments or drainage. It can support a first model of how anticipatory assistance timing changes household flood impacts, if assignment, household IDs, asset outcomes and baseline covariates can be linked correctly. Catalog listings indicate licensed microdata; obtain authorized access and review codebook/permissions before training. |
| [WFP / World Bank: Nepal Forecast-Based Anticipatory Action Impact Evaluation 2022–2023](https://microdata.worldbank.org/catalog/8010) | Household survey across 138 villages (70 control and 68 treatment villages), three rounds; randomized timing of physical cash transfers after flood peak versus one month later; food security, coping, wellbeing and expenditure outcomes. | Strong randomized evidence for timing of post-flood assistance, but not a pre-flood physical precaution; documented outcomes are mainly welfare/coping rather than direct asset damage. Catalog listings indicate licensed microdata. Secondary candidate. |
| [Yale / Inclusion Economics: Community Messengers Turn Flood Forecasts into Protection (September 2026)](https://ie.yale.edu/research/community-messengers-turn-flood-forecasts-protection) | Four-year randomized trial (2022–2025) across 319 North Bihar panchayats, with 5,582 households followed over four monsoons. Trained community messengers relayed official forecasts; reported outcomes include home flooding, house damage, food insecurity and borrowing. | Excellent intervention match for warning dissemination. The public policy brief provides aggregate results, not household/panchayat-level microdata for the current trainer. Request authorized microdata, treatment assignment, cluster IDs, panel structure, survey weights, codebook and usage terms. |
| [Bril et al. (2026): open coupled-model dataset for flood risk reduction measures](https://zenodo.org/records/15488420) ([paper](https://doi.org/10.1029/2025WR041436)) | Open model inputs, code and outputs for Geul catchment simulations of dry-proofing, wet-proofing, retention ponds, reforestation and natural grassland; includes modeled flood extent, depths, damage and costs. Main results archive is 10.2 GB, with additional archives. | Useful complementary **simulated** training source, not observed intervention records. It can train a clearly labelled simulation-surrogate ML model for measures represented in the model, but is specific to the Geul catchment and model assumptions. Never mix simulated labels with empirical treatment outcomes as if they were the same target. |
| [FEMA Hazard Mitigation Assistance mitigated properties](https://catalog.data.gov/dataset/hazard-mitigation-assistance-mitigated-properties) and [funded projects](https://catalog.data.gov/dataset/hazard-mitigation-assistance-projects) | Real records of funded mitigation projects and properties, joinable by project identifier. | Useful intervention inventory for US projects. Public descriptions do not establish a clean property-level join to post-event damage/claims outcomes. Not a ready causal training table. |
| [India Flood Inventory-Impacts v4](https://zenodo.org/records/16994648) | Open Indian flood-event and district-impact data for 1967–2023, including district flood severity, flooded area and impacts. | Valuable Indian hazard/outcome context and possible external validation, but contains no treatment/intervention assignment. |
| [FLODIS open flood-impact dataset](https://www.nature.com/articles/s41597-023-02376-9) | Flood footprints linked to displacement, fatalities and economic-damage records. | Outcome source only; no verified intervention assignment. |
| [CWC assessment of flood-affected and protected areas in India](https://www.pib.gov.in/Pressreleaseshare.aspx?PRID=2037094&lang=1&reg=3) | District-scale flood-affected and protected-area statistics over 1986–2022. | Useful context, but aggregate protected/affected area is not a matched site-event intervention panel. |
| [World Bank IEG evaluation of disaster-risk-reduction activities](https://ieg.worldbank.org/evaluations/reducing-disaster-risks-natural-hazards/chapter-4-effectiveness-world-banks-disaster) | Documents limitations in outcome-level measurement across disaster-risk-reduction portfolios. | Reinforces the need to distinguish measured damage reduction from project outputs and spending. |

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

No dataset has yet been downloaded into the repository or approved for training.
The best actionable empirical lead is the Bangladesh 2024 WFP/World Bank
randomized evaluation: its metadata documents randomized transfer timing and a
separate asset-damage file. The catalog classifies the microdata as licensed,
so authorized access and exact record linkage must be confirmed first. This
supports a narrowly scoped first model for the effect of anticipatory
cash-transfer timing on household flood impacts—not a general ranking of every
physical precaution.

In parallel, the open Bril et al. coupled-model archive provides simulated
counterfactual damage under several flood measures. It may support a separate
simulation-surrogate model, clearly labelled as model-generated rather than
observed causal evidence. Keep empirical and simulated training tracks
separate. India Flood Inventory v4 can support Indian flood context/validation,
but has no intervention assignment. The current empirical trainer remains
blocked until a provenance-verified, compatible episode table is supplied.


## Geul simulation archive inspection

The open Geul archive is a potentially useful separate training track for
simulation-surrogate learning. Its published Zenodo record lists a 10.2 GB
`final_results.zip`, a 994.2 MB `geulnew.zip` and a 116 MB `scripts.zip`.
Do not assume a particular CSV schema or train from file names alone. After
obtaining the archive from the publisher, inspect it without extracting the
full 10+ GB archive:

```bash
python scripts/inspect_intervention_archive.py \
  --archive path/to/final_results.zip \
  --output reports/geul_archive_manifest.json
```

The manifest lists members and samples headers from small CSV/TSV files.
Review those columns against the paper, supporting information and model
scripts before defining scenario, intervention, damage, cost, spatial unit
and baseline/counterfactual pairings. The inspector does not train a model.
Keep all generated simulation targets in a separate registry from observed
trial/field outcomes. Any surrogate must be tested on held-out scenarios or
spatial units, and its outputs remain Geul-model-conditioned until a separate
Kochi-specific hydrological and exposure validation establishes transfer.

Source: Bril et al., Zenodo dataset
https://zenodo.org/records/15488420 (GPL-3.0 per the article's data statement).
