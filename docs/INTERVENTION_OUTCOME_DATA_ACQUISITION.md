# Real intervention-outcome data acquisition plan

**Purpose:** obtain genuine, documented records linking a disaster-risk-reduction intervention to observed outcomes. This is separate from hazard forecasting and from simulated intervention experiments.

## Decision: use a tiered evidence strategy

Do not fabricate episode-level labels from reports, maps, weather records, or synthetic data. Keep three evidence tracks separate:

1. **Licensed household microdata:** potentially suitable for supervised causal-effect research after access approval, codebook review, and a documented data-use agreement.
2. **Published impact evaluations:** suitable now for a cited evidence library and conservative action guidance. Aggregate estimates are not individual training rows.
3. **Simulation outputs:** suitable only for a separately labelled simulation-surrogate model within the simulation's domain. Never merge them with real-world causal training data or claim transfer to Kochi.

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
- Research summary: https://egc.yale.edu/research/community-level-flood-early-warning-systems-vulnerable-households-india
- Trial: community messengers relayed official flood warnings through local channels, compared with smartphone alerts alone; 319 panchayats across Bihar.
- Published outcomes include warning receipt and timing, household preparation, water entering homes, house damage, hunger, and distress borrowing. The published brief reports meaningful protection during severe flooding.
- Current data status for this project: **published results located; household-level downloadable microdata not verified**. Do not scrape or reverse-engineer individual records from aggregate charts. Contact the study team through the official research page if a properly supervised data request is appropriate.
- Immediate use: add the evaluation as a cited evidence record for community warning dissemination. Do not treat published average effects as thousands of synthetic training samples.

## Priority 4 — Geul flood mitigation simulation archive

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

**Current conclusion:** the strongest actionable real-data route is the licensed Bangladesh evaluation because its catalog exposes both randomized timing/administrative records and an asset-damage module. The missing ingredient is lawful, approved access to the underlying microdata. The Bihar trial gives directly relevant Indian evidence for community warning dissemination, but its raw microdata availability remains unverified. No responsible implementation can manufacture that missing access or data.

## Additional inference guard — observed training support

The observational intervention learner now records numeric feature ranges and observed categorical levels from its training partition. Context-specific inference is withheld if any numeric value falls outside the observed training range, if a categorical level was never observed, or if the model artifact predates this support profile. This is a conservative extrapolation guard, not proof that a point inside every marginal range is jointly well-supported; multivariate overlap and context-specific uncertainty remain unresolved. Existing intervention artifacts must be retrained to include the support profile.

The training CLI now requires an explicit outcome_unit and outcome_direction: "lower_is_better" in the provenance sidecar. It no longer silently assigns a generic damage-severity unit to an arbitrary numeric outcome. This prevents a model card from presenting an incorrect unit or direction.
