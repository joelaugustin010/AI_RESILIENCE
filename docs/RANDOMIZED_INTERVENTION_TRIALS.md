# Cluster-randomized multi-arm intervention model

## Why this is separate

The existing `src/intervention_effectiveness.py` pipeline is an observational
binary action-vs-no-action learner. It must not be used unchanged for a
cluster-randomized, three-arm trial. The Bangladesh WFP/World Bank evaluation
randomized villages to different transfer-timing arms; assignment is the
treatment for the primary intention-to-treat (ITT) estimand.

`src/randomized_intervention_trials.py` adds a separate research path for
multi-arm randomized studies. It compares one assigned arm with a declared
reference arm, uses the known assignment probabilities from the trial protocol,
holds out entire randomization clusters, cross-fits outcome models by cluster,
learns an exploratory conditional effect model from doubly robust scores, and
uses cluster bootstrap intervals for held-out average and policy effects.

## Required input contract

One row must represent one independent analysis episode, such as one
household-season or household-survey-round. Required columns:

- `episode_id`: unique household/episode identifier after outcome aggregation;
- `assignment_cluster_id`: the actual randomization unit (e.g. village);
- `assigned_arm`: randomized arm, not whether a transfer was received;
- `damage_outcome`: comparable numeric post-event outcome, lower is better;
- explicitly approved pre-randomization covariates only.

For asset-level survey files, aggregate asset damage to the household using a
pre-specified and documented rule before fitting. Do not count 100,000 assets
as 100,000 independent households. The same household must not appear as
multiple independent episodes unless repeated-measure dependence is explicitly
handled in the analysis design.

The caller must supply the complete assignment-probability vector from the published
randomization protocol. Its keys must exactly match the observed randomized
arms and every probability must be finite and strictly between zero and one.
Do not estimate assignment probabilities from observed outcomes. Probabilities for the two compared arms are renormalised to sum to one
for the pairwise target population. This first implementation assumes fixed arm probabilities across
clusters; stratified or block randomization with varying probabilities needs
the cluster-specific assignment probabilities and must not be forced into this
API.

## Estimand and safeguards

- Primary: pairwise ITT effect of being assigned to the selected arm versus the reference arm, conditional on assignment to one of those two arms. Other arms are excluded, never silently recoded as controls.
- It does not estimate the effect of actually receiving or spending the cash.
  An as-treated analysis would be confounded; compliance effects require a
  separately specified instrumental-variable estimand.
- The train/test split is by whole randomization cluster. A cluster never
  appears in both sets.
- Cross-fitting is grouped by cluster.
- Uncertainty is bootstrapped at the randomization-cluster level.
- The model refuses insufficient cluster counts, invalid or incomplete
  assignment-probability vectors, invalid holdout fractions, treatment leakage,
  blank cluster/arm identifiers, and clusters assigned to multiple arms.
- Held-out average ITT and learned-policy intervals are cluster-bootstrap
  intervals. They assess the average comparison and the learned policy on the
  held-out population; they are not confidence intervals for a particular
  user's context.
- `estimate(context)` returns an exploratory CATE point estimate only.
  Context-specific uncertainty and pairwise superiority between two actions
  are not estimated. Such a point estimate must not be used to claim that one
  precaution is the best choice for that context.
- A learned CATE policy is exploratory. It is not a validated operational
  recommendation.

## Reproducible training command

After authorized access, codebook review, aggregation and provenance approval,
the training entry point is:

```bash
python scripts/train_randomized_intervention_trials.py \
  --data data/authorized/household_trial_episodes.csv \
  --provenance data/authorized/trial_provenance.json \
  --reference-arm standard_post_shock \
  --treatment-arms anticipatory,rapid_post_shock
```

The provenance JSON must include the source and protocol references, data
permission basis, randomization unit, assignment definition, outcome definition
and unit, pre-randomization feature allowlist, and the complete assignment
probability map. The script refuses synthetic data, unknown/pending access
permission, mismatched arm labels and incomplete provenance. It writes a
separate randomized-trial registry and model artifacts; it does not mix these
trial arms into the generic physical-precaution catalogue.

## Bangladesh candidate scope

If licensed microdata access is granted and the codebook confirms the joins,
this can support comparisons among the study's cash-transfer timing arms for
the measured household flood outcomes. It cannot identify the effect of
drainage upgrades, embankments, sandbags, household retrofits, or other
unrandomized physical actions. The trial's actual arm labels, randomization
probabilities, assignment-cluster IDs, attrition, survey weights and outcome
construction must be verified before creating the analysis table.

## Validation still required

This module is code, not a trained model. Unit tests use generated fixtures
only to test software behavior; those fixtures are never accepted as training
data. Real licensed data, protocol review, a pre-analysis plan, design-aware
weights/strata handling, sensitivity checks, independent replication and
external validation are still required. It must not be described as perfect,
validated, or ready for disaster-response decisions.
