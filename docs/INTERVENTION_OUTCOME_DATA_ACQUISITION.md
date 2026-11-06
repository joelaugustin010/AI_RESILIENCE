# Real intervention-outcome data acquisition plan

**Purpose:** obtain genuine, documented records linking a disaster-risk-reduction intervention to observed outcomes. This is separate from hazard forecasting and from simulated intervention experiments.

## Decision: use a tiered evidence strategy

Do not fabricate episode-level labels from reports, maps, weather records, or synthetic data. Keep three evidence tracks separate:

1. **Licensed household microdata:** potentially suitable for supervised causal-effect research after access approval, codebook review, and a documented data-use agreement.
2. **Published impact evaluations:** suitable now for a cited evidence library and conservative action guidance. Aggregate estimates are not individual training rows.
3. **Simulation outputs:** suitable only for a separately labelled simulation-surrogate model within the simulation's domain. Never merge them with real-world causal training data or claim transfer to Kochi.


## Priority 0 — Kochi Operation Breakthrough (local intervention evidence lead)

- Official KSDMA event/project record: https://sdma.kerala.gov.in/%E0%B4%95%E0%B5%8A%E0%B4%9A%E0%B5%8D%E0%B4%9A%E0%B4%BF-2019/
- KSDMA states that Kochi City flooded during the 21 October 2019 rainy spell, with critical assets including the main power sub-station and arterial roads affected; it records approval of Operation Breakthrough under GO (Ms) No. 35/2019/DMD dated 11 November 2019.
- This is the most geographically relevant intervention lead found so far. It is **not yet an effectiveness dataset**: the public summary does not provide a matched pre/post damage series, intervention completion dates and geographies, treatment coverage/intensity, comparable untreated locations, or counterfactual outcomes.
- Related state context: Kerala State Disaster Management Authority's post-disaster needs assessment describes damage to flood-protection and drainage infrastructure; CAG Report No. 6 of 2021 audits preparedness and response to floods in Kerala. These can help identify assets, projects, implementation and governance records, but neither should be treated as a causal outcome table without record-level linkage.
- Required follow-up evidence: the GO and project scope; ward/asset-level work orders and completion dates; geospatial intervention footprints and capacity/design changes; maintenance records; rainfall/tide/drainage and water-level observations; geocoded inundation depth/duration; asset and household damage before/after; exposed population and infrastructure; and comparable untreated or not-yet-treated locations/events. Record data owner, access terms, collection method and definitions.
- Potential design: a carefully scoped event/site panel or difference-in-differences/event-study only if implementation timing and comparison assumptions are defensible. Check for concurrent works, changing exposure, rainfall/tide differences, spillovers and changes in reporting. A simple before/after comparison is not sufficient to attribute improvement to the project.
- Decision: prioritize this local evidence investigation before attempting to transfer foreign physical-mitigation estimates to Kochi. Until the missing records and a defensible design are obtained, show Operation Breakthrough as a documented local intervention example, not a measured damage-reduction effect or a trained ML label.


## Priority 1 — Bangladesh 2024 Forecast-Based Anticipatory Action Impact Evaluation

- Catalog: https://microdata.worldbank.org/catalog/8009
- DOI: https://doi.org/10.48529/ezxd-6a30
- Study: WFP / World Bank evaluation of forecast-triggered cash transfers during 2024 flooding in the Jamuna basin.
- Design: randomized timing of cash transfers, with anticipatory assistance before the flood peak and later-response comparison arms.
- Relevant outcomes: household preparedness, coping, food security, migration, consumption, and asset damage.
- Catalogued data include three survey rounds, administrative/randomization data, GIS buffers, and an asset-damage module. The asset module documents whether owned assets were damaged and whether they were lost, swept away, or damaged at different severities.
- Access: **licensed / human approval required**. Do not attempt to bypass access controls. Because this project is being developed by a minor, a parent/guardian, teacher, or school supervisor should handle any data-access request and agree to the applicable terms.
- Permitted research question after approval: estimate the effect of *timing of cash assistance* on measured household outcomes, respecting the randomized assignment and study protocol.
- Not supported: claiming that cash transfers are equivalent to physical flood-proofing, drainage, evacuation, or structural interventions; transferring household-level effects to Kochi without validation.

## Priority 2 — Nepal 2022–2023 Forecast-Based Anticipatory Action Impact Evaluation

- Catalog: https://microdata.worldbank.org/catalog/8010
- Study: WFP / World Bank household survey evaluation in flood-affected districts.
- Design: randomized timing of post-flood cash support (immediate after peak versus delayed by about one month).
- Outcomes include food security, psychological wellbeing, and coping strategies across three survey rounds.
- Access: licensed microdata; approval and terms must be checked by the responsible adult/research supervisor.
- Research question: effects of earlier versus later post-shock cash support. This does not identify effects of physical mitigation measures.

## Priority 3 — Bihar, India community flood-warning dissemination trial

- Published evaluation: https://ie.yale.edu/research/community-messengers-turn-flood-forecasts-protection
- Research summary: https://egc.yale.edu/building-community-level-flood-early-warning-systems-vulnerable-households-india
- Trial: four monsoon seasons (2022–2025), 319 panchayats across 12 north Bihar districts, testing trained community messengers relaying official forecasts against smartphone alerts alone.
- The September 2026 research brief reports improvements in warning receipt and lead time, preparedness, and reduced household floodwater entry and damage in severely flooded areas. The result is directly relevant to warning dissemination, not to structural mitigation or other hazards.
- Current data status for this project: **published randomized-trial findings located; household-level downloadable microdata not verified**. Do not scrape or reverse-engineer individual records from aggregate results. Contact the study team through the official research page if a properly supervised data request is appropriate.
- Immediate use: cite the study in a clearly labelled evidence record for community warning dissemination. Do not treat published average effects as row-level training samples.

## Priority 4 — Netherlands 2021 household flood-damage mitigation survey

- Publication: https://doi.org/10.1029/2022WR034192
- Data DOI stated by the publication: https://doi.org/10.4121/21603348
- Study: Endendijk et al. (2023), *Flood Vulnerability Models and Household Flood Damage Mitigation Measures: An Econometric Analysis of Survey Data*.
- Relevance: household-level flood damage observations and implemented emergency/structural flood-damage mitigation measures, with hazard, exposure and vulnerability covariates. The paper uses an instrumental-variable strategy to address selection into mitigation; it reports that emergency and structural measures reduce damage, while acknowledging limits in identifying multiple simultaneous measures and depth-specific effects.
- Access/licence status: the paper points to the 4TU.ResearchData record, but the dataset landing page, file list, exact licence, and downloadability have **not yet been verified**. Do not assume that a repository DOI implies unrestricted reuse. Verify record metadata and terms before downloading or training.
- Model fit: potentially the closest located real-world household dataset for physical flood-mitigation outcomes. It is observational and from the Netherlands, so it cannot validate Kochi effects. The current learner's minimum sample/cluster and time-split requirements may be unsuitable for a single-event survey; inspect the actual design before adapting thresholds. Do not lower evidence gates just to make training run.
- Next step after access verification: inspect codebook, instrument, household/site identifiers, intervention definitions, damage ratios/units, survey design, and missingness. Determine whether a separate design-aware IV/observational estimator is required rather than forcing these data into the current repeated-episode learner.

## Priority 5 — Geul flood mitigation simulation archive

- Dataset: https://zenodo.org/records/15488420
- DOI: https://doi.org/10.5281/zenodo.15488420
- License reported by the archive metadata: CC BY 4.0.
- Contains modelled intervention scenarios such as building-level flood measures and nature-based measures.
- Use only after the local archive is fully downloaded, checksum-verified, inspected, and its variables/units/scenario design are understood.
- Model label must say **simulation surrogate / Geul catchment**. It is not a real-world intervention trial and does not prove causal effectiveness in Kochi.

## Data acceptance contract before training

Every candidate training source must pass all of these checks:

- Documented source, owner, collection dates, geographic scope, licence/access terms, and version.
- A defined unit of analysis and stable episode/site/household identifiers.
- A clearly specified intervention, treatment assignment or implementation status, and treatment timing.
- A measurable outcome with definition, exact unit, observation window, and direction. The current learner requires an explicitly documented lower_is_better outcome; higher-is-better outcomes must be transformed with a documented, reproducible rule before training.
- Pre-intervention covariates only; no post-treatment variables or outcome leakage in features.
- A defensible comparison group and study design; assignment probabilities or randomization fields where available.
- Site/cluster identifiers and event/time boundaries for leakage-resistant splits.
- Missingness, attrition, non-compliance, spillovers, treatment-version differences, and survey weights/design documented.
- Reproducible import, validation report, and source-to-model lineage.

A dataset that lacks treatment assignment or implementation details may still be useful for descriptive evidence, but it must not be passed to the causal intervention learner.

## Model integration rules

1. Keep the existing intervention model fail-closed. No real-data model card may be emitted until the data acceptance contract passes.
2. Keep Bangladesh cash-transfer timing, Nepal post-shock cash timing, Bihar warning dissemination, physical mitigation, and Geul simulation in distinct intervention families.
3. Do not pool unlike interventions into a single treatment label such as `precaution=1`.
4. Do not use published aggregate percentages as row-level examples or expand them into pseudo-records.
5. Report study-specific effects and uncertainty only within the supported study population and intervention definition.
6. No recommendation may be described as the proven best action for Kochi unless local or transportable evidence and validation support that claim.
7. Preserve a clear distinction between (a) observed outcomes, (b) randomized/observational effect estimates, (c) simulation results, and (d) expert/evidence-based action guidance.

## Next execution sequence

1. A responsible adult/teacher reviews the World Bank licensed-data terms and submits an access request if appropriate.
2. Once authorized files are obtained, preserve the original files, licence, codebook, and checksums; never commit restricted microdata to the public repository.
3. Inspect codebooks and randomization/administrative files before writing an adapter. Resolve treatment arms, survey rounds, household keys, asset modules, and outcome timing.
4. Build a local-only, reproducible adapter that emits the project's intervention episode schema and a separate data-quality report.
5. Run design-aware causal analysis and cluster-level uncertainty checks; validate on held-out sites/events where the study design permits.
6. Publish only non-sensitive derived metrics, model cards, provenance, and limitations.

**Current conclusion:** there are now three distinct real-world evidence leads: (1) the Netherlands 2021 household mitigation survey is the closest identified candidate for physical flood-damage-reduction measures, but its actual dataset access and licence must still be verified; (2) the Bangladesh randomized cash-timing evaluation has an asset-damage module but requires licensed access; and (3) the Bihar randomized warning-dissemination trial has directly relevant published Indian results, but household microdata availability is unverified. Geul remains simulation-only. No source should be described as integrated or trained until the raw files, rights, schema, and study design have been checked.

## Additional inference guard — observed training support

The observational intervention learner now records numeric feature ranges and observed categorical levels from its training partition. Context-specific inference is withheld if any numeric value falls outside the observed training range, if a categorical level was never observed, or if the model artifact predates this support profile. This is a conservative extrapolation guard, not proof that a point inside every marginal range is jointly well-supported; multivariate overlap and context-specific uncertainty remain unresolved. Existing intervention artifacts must be retrained to include the support profile.

The training CLI now requires an explicit outcome_unit and outcome_direction: "lower_is_better" in the provenance sidecar. It no longer silently assigns a generic damage-severity unit to an arbitrary numeric outcome. This prevents a model card from presenting an incorrect unit or direction.

Held-out policy evaluation is also restricted to contexts inside the training support profile. Unsupported test contexts are assigned no learned intervention by the evaluated policy, and a research signal is withheld unless at least 80% of the held-out contexts meet the marginal support guard. This does not replace multivariate overlap diagnostics or context-specific uncertainty intervals.

## Newly discovered evidence and data leads (research update)

The 2023 Netherlands study explicitly states that the underlying household flood-damage dataset is deposited at 4TU.ResearchData under DOI 10.4121/21603348. The study's empirical analysis uses instrumental variables to address selection into flood-damage mitigation; it also documents limitations around simultaneous measures and depth-specific effects. This is a high-priority dataset to verify, not a claim that the files are already downloaded or reusable. The 2026 Yale/Inclusion Economics brief now reports the four-year Bihar randomized evaluation's household protection outcomes; these published aggregate results strengthen the evidence library but remain unsuitable as individual training rows without lawful microdata.


## Additional candidate — Pakistan 2023 flood-warning survey (screening only)

- Repository record: https://zenodo.org/records/23455118
- DOI: https://doi.org/10.5281/zenodo.23455118
- Record published: 18 October 2026.
- The record describes anonymized questionnaire data from 350 flood-affected households in Rajanpur District after the 2023 floods, alongside PLS-SEM result workbooks and the survey instrument.
- **Important limitations:** the Zenodo record's Rights/License field is blank in the inspected metadata; reuse permission is therefore not established. The record describes a post-flood questionnaire and PLS-SEM analyses, not a randomized assignment design. The published metadata alone do not establish a validated household damage outcome, intervention implementation/timing, comparison group, cluster structure, or pre-treatment covariate set.
- Decision: retain as a **candidate for codebook and rights review only**. Do not download into the project, train on it, infer causal intervention effects, or treat its PLS-SEM outputs as episode-level training labels unless the licence, questionnaire, variable definitions, and study design are independently verified. An adult research supervisor should review any reuse terms and contact the data author if necessary.
- It may ultimately support descriptive research on warning quality and protective actions; it is not presently accepted by either intervention training pipeline.
