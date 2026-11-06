"""Cluster-randomized multi-arm intervention-effect research.

This module is intentionally separate from the observational binary-action
trainer. It estimates intention-to-treat (ITT) contrasts from randomized
assignment, preserving the randomization cluster as the independent unit.
It does not infer effects of treatment receipt or compliance.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import ExtraTreesRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


class TrialDataError(ValueError):
    """The trial data do not match the declared randomized design."""


@dataclass
class RandomizedContrast:
    treatment_arm: str
    reference_arm: str
    feature_columns: list[str]
    preprocessor: Any
    cate_model: Any
    report: dict[str, Any]

    def estimate(self, context: Mapping[str, Any]) -> dict[str, Any]:
        if not self.report.get("eligible_for_research_ranking", False):
            return {"available": False, "status": self.report["status"],
                    "reason": self.report["status_reason"]}
        missing = [c for c in self.feature_columns if c not in context]
        if missing:
            return {"available": False, "status": "CONTEXT_INCOMPLETE",
                    "missing_features": missing}
        x = self.preprocessor.transform(pd.DataFrame(
            [{c: context[c] for c in self.feature_columns}]
        ))
        effect = float(self.cate_model.predict(x)[0])
        return {
            "available": True,
            "status": "RANDOMIZED_TRIAL_RESEARCH_SIGNAL_NOT_VALIDATED",
            "treatment_arm": self.treatment_arm,
            "reference_arm": self.reference_arm,
            "estimated_itt_damage_change": effect,
            "estimated_damage_reduction": -effect,
            "outcome_unit": self.report["outcome_unit"],
            "warning": "Exploratory heterogeneous ITT estimate; not a guaranteed or operational effect.",
        }


def validate_trial_frame(
    frame: pd.DataFrame,
    feature_columns: Sequence[str],
    *,
    cluster_col: str = "assignment_cluster_id",
    arm_col: str = "assigned_arm",
    outcome_col: str = "damage_outcome",
) -> None:
    # Check forbidden post-assignment fields before column-presence validation:
    # a leakage attempt must be reported as leakage even when the column is absent.
    forbidden = {
        "received_treatment", "implemented", "treatment_received",
        "post_treatment", "post_intervention", "damage_outcome",
        "assigned_arm", "assignment_cluster_id", "episode_id",
    }
    bad = [c for c in feature_columns
           if c.lower() in forbidden or any(
               token in c.lower() for token in
               ("outcome", "damage_after", "post_", "after_", "received",
                "implemented", "assigned_arm", "treatment", "recovery")
           )]
    if bad:
        raise TrialDataError(f"Treatment/post-treatment leakage in feature list: {bad}")
    required = {"episode_id", cluster_col, arm_col, outcome_col, *feature_columns}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise TrialDataError(f"Missing trial columns: {missing}")
    if frame.empty:
        raise TrialDataError("Trial dataset is empty.")
    if frame["episode_id"].isna().any() or frame["episode_id"].astype(str).str.strip().eq("").any():
        raise TrialDataError("episode_id must be present for every observation.")
    if frame[cluster_col].isna().any() or frame[arm_col].isna().any():
        raise TrialDataError("Assignment cluster and assigned arm cannot be missing.")
    if frame.groupby(cluster_col, dropna=False)[arm_col].nunique().max() != 1:
        raise TrialDataError("A randomization cluster appears in more than one assigned arm.")
    if frame["episode_id"].astype(str).duplicated().any():
        raise TrialDataError(
            "Each episode_id must be one aggregated observation; aggregate asset-level rows "
            "to the household/episode before fitting to avoid pseudoreplication."
        )
    outcome = pd.to_numeric(frame[outcome_col], errors="coerce")
    if outcome.isna().any() or not np.isfinite(outcome.to_numpy(float)).all():
        raise TrialDataError("Damage outcome must be finite numeric data.")
    forbidden = {
        "received_treatment", "implemented", "treatment_received",
        "post_treatment", "post_intervention", "damage_outcome",
        "assigned_arm", "assignment_cluster_id", "episode_id",
    }
    bad = [c for c in feature_columns
           if c.lower() in forbidden or any(
               token in c.lower() for token in
               ("outcome", "damage_after", "post_", "after_", "received",
                "implemented", "assigned_arm", "treatment", "recovery")
           )]
    if bad:
        raise TrialDataError(f"Treatment/post-treatment leakage in feature list: {bad}")
    if not feature_columns:
        raise TrialDataError("At least one pre-randomization covariate is required.")
    if frame[list(feature_columns)].isna().all(axis=0).any():
        raise TrialDataError("A covariate is entirely missing.")


def _preprocessor(frame: pd.DataFrame, features: Sequence[str]) -> ColumnTransformer:
    numeric = [c for c in features if pd.api.types.is_numeric_dtype(frame[c])]
    categorical = [c for c in features if c not in numeric]
    transforms = []
    if numeric:
        transforms.append(("numeric", SimpleImputer(strategy="median"), numeric))
    if categorical:
        transforms.append(("categorical", Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]), categorical))
    return ColumnTransformer(transforms, remainder="drop")


def _cluster_bootstrap_ci(
    scores: np.ndarray, clusters: np.ndarray, *, seed: int, draws: int = 2000
) -> list[float]:
    unique = np.unique(clusters)
    if len(unique) < 2:
        return [float("nan"), float("nan")]
    positions = {g: np.flatnonzero(clusters == g) for g in unique}
    rng = np.random.default_rng(seed)
    means = []
    for _ in range(draws):
        sampled = rng.choice(unique, len(unique), replace=True)
        idx = np.concatenate([positions[g] for g in sampled])
        means.append(float(np.mean(scores[idx])))
    return [float(x) for x in np.quantile(means, [0.025, 0.975])]


def fit_randomized_contrast(
    frame: pd.DataFrame,
    *,
    treatment_arm: str,
    reference_arm: str,
    assignment_probabilities: Mapping[str, float],
    feature_columns: Sequence[str],
    outcome_unit: str,
    cluster_col: str = "assignment_cluster_id",
    arm_col: str = "assigned_arm",
    outcome_col: str = "damage_outcome",
    test_fraction: float = 0.25,
    seed: int = 42,
    min_clusters_per_arm: int = 20,
) -> RandomizedContrast:
    """Fit a cross-fitted DR CATE for one randomized arm vs another.

    Assignment probabilities must come from the documented randomization
    design (not estimated from outcomes). The split holds out whole assignment
    clusters. All effects are ITT by assigned arm, regardless of compliance.
    Lower damage outcomes are better; negative effects indicate benefit.
    """
    validate_trial_frame(frame, feature_columns, cluster_col=cluster_col,
                         arm_col=arm_col, outcome_col=outcome_col)
    if treatment_arm == reference_arm:
        raise TrialDataError("Treatment and reference arms must differ.")
    for arm in (treatment_arm, reference_arm):
        p = assignment_probabilities.get(arm)
        if p is None or not np.isfinite(p) or p <= 0 or p >= 1:
            raise TrialDataError(f"Documented positive assignment probability required for arm {arm!r}.")
    probability_total = sum(float(v) for v in assignment_probabilities.values())
    if not np.isclose(probability_total, 1.0, atol=1e-6):
        raise TrialDataError(
            "Supply the complete, documented arm-probability vector; probabilities must sum to one."
        )

    data = frame.loc[frame[arm_col].isin([treatment_arm, reference_arm])].copy()
    data[outcome_col] = pd.to_numeric(data[outcome_col], errors="raise")
    cluster_arms = data[[cluster_col, arm_col]].drop_duplicates()
    by_arm = {
        arm: cluster_arms.loc[cluster_arms[arm_col] == arm, cluster_col].astype(str).unique()
        for arm in (treatment_arm, reference_arm)
    }
    counts = {arm: int(len(by_arm[arm])) for arm in by_arm}
    status = "INSUFFICIENT_RANDOMIZED_CLUSTERS"
    empty = {"status": status, "eligible_for_research_ranking": False,
             "status_reason": f"Need at least {min_clusters_per_arm} independent clusters per arm; observed {counts}.",
             "cluster_counts": counts, "validated": False}
    if any(n < min_clusters_per_arm for n in counts.values()):
        return RandomizedContrast(treatment_arm, reference_arm, list(feature_columns),
                                  None, None, empty)

    rng = np.random.default_rng(seed)
    test_clusters: set[str] = set()
    for arm, clusters in by_arm.items():
        shuffled = rng.permutation(clusters)
        n_test = max(2, int(round(len(shuffled) * test_fraction)))
        n_test = min(n_test, len(shuffled) - 2)
        test_clusters.update(str(x) for x in shuffled[:n_test])
    is_test = data[cluster_col].astype(str).isin(test_clusters)
    train, test = data.loc[~is_test].copy(), data.loc[is_test].copy()
    train_counts = train.groupby(arm_col)[cluster_col].nunique().to_dict()
    test_counts = test.groupby(arm_col)[cluster_col].nunique().to_dict()
    if any(train_counts.get(a, 0) < 5 or test_counts.get(a, 0) < 2
           for a in (treatment_arm, reference_arm)):
        empty.update({"status_reason": "Cluster holdout left too few clusters in an arm.",
                      "train_cluster_counts": train_counts, "test_cluster_counts": test_counts})
        return RandomizedContrast(treatment_arm, reference_arm, list(feature_columns),
                                  None, None, empty)

    prep = _preprocessor(train, feature_columns)
    x_train = prep.fit_transform(train[list(feature_columns)])
    x_test = prep.transform(test[list(feature_columns)])
    a_train = (train[arm_col].to_numpy() == treatment_arm).astype(int)
    y_train = train[outcome_col].to_numpy(float)
    groups = train[cluster_col].astype(str).to_numpy()
    n_groups = len(np.unique(groups))
    folds = min(5, n_groups)
    if folds < 2:
        raise TrialDataError("At least two training clusters are required for cross-fitting.")
    pseudo = np.full(len(train), np.nan)
    splitter = GroupKFold(n_splits=folds)
    # This estimator conditions on assignment to one of the two compared
    # arms. Renormalise the protocol probabilities for that pair; other trial
    # arms are not silently treated as the reference group.
    pair_probability = (
        float(assignment_probabilities[treatment_arm])
        + float(assignment_probabilities[reference_arm])
    )
    p_a = float(assignment_probabilities[treatment_arm]) / pair_probability
    p_r = float(assignment_probabilities[reference_arm]) / pair_probability
    for fold, (fit_idx, held_idx) in enumerate(splitter.split(x_train, a_train, groups)):
        if len(np.unique(a_train[fit_idx])) != 2:
            raise TrialDataError("A cross-fitting fold lacks one of the comparison arms.")
        models = {}
        for arm_value in (0, 1):
            model = RandomForestRegressor(
                n_estimators=250, min_samples_leaf=8, max_features=0.8,
                random_state=seed + fold * 11 + arm_value, n_jobs=-1,
            )
            model.fit(x_train[fit_idx][a_train[fit_idx] == arm_value],
                      y_train[fit_idx][a_train[fit_idx] == arm_value])
            models[arm_value] = model
        mu_r = models[0].predict(x_train[held_idx])
        mu_a = models[1].predict(x_train[held_idx])
        observed_arm = a_train[held_idx]
        observed_y = y_train[held_idx]
        # Known randomized assignment probabilities; no estimated propensity.
        pseudo[held_idx] = ((mu_a - mu_r)
            + observed_arm * (observed_y - mu_a) / p_a
            - (1 - observed_arm) * (observed_y - mu_r) / p_r)

    cate = ExtraTreesRegressor(
        n_estimators=400, min_samples_leaf=10, max_features=0.8,
        random_state=seed, n_jobs=-1,
    )
    cate.fit(x_train, pseudo)

    a_test = (test[arm_col].to_numpy() == treatment_arm).astype(int)
    y_test = test[outcome_col].to_numpy(float)
    models = {}
    for arm_value in (0, 1):
        model = RandomForestRegressor(
            n_estimators=300, min_samples_leaf=8, max_features=0.8,
            random_state=seed + 900 + arm_value, n_jobs=-1,
        )
        model.fit(x_train[a_train == arm_value], y_train[a_train == arm_value])
        models[arm_value] = model
    mu_r = models[0].predict(x_test)
    mu_a = models[1].predict(x_test)
    dr_test = ((mu_a - mu_r) + a_test * (y_test - mu_a) / p_a
               - (1 - a_test) * (y_test - mu_r) / p_r)
    test_group_values = test[cluster_col].astype(str).to_numpy()
    ate_ci = _cluster_bootstrap_ci(dr_test, test_group_values, seed=seed + 1001)
    ate = float(np.mean(dr_test))
    predicted_effect = cate.predict(x_test)
    policy_choose_treatment = predicted_effect < 0
    policy_scores = np.where(policy_choose_treatment, dr_test, 0.0)
    policy_ci = _cluster_bootstrap_ci(policy_scores, test_group_values, seed=seed + 1002)
    policy_effect = float(np.mean(policy_scores))
    eligible = bool(ate_ci[1] < 0 and policy_ci[1] < 0)
    return RandomizedContrast(
        treatment_arm, reference_arm, list(feature_columns), prep, cate,
        {
            "status": ("RANDOMIZED_TRIAL_RESEARCH_SIGNAL_NOT_VALIDATED" if eligible
                       else "NO_CLEAR_HELDOUT_DAMAGE_REDUCTION_SIGNAL"),
            "eligible_for_research_ranking": eligible,
            "validated": False,
            "estimand": "Intention-to-treat effect of randomized assignment, not treatment receipt.",
            "treatment_arm": treatment_arm, "reference_arm": reference_arm,
            "assignment_probabilities": dict(assignment_probabilities),
            "outcome_unit": outcome_unit, "outcome_direction": "lower_is_better",
            "cluster_counts": counts, "train_cluster_counts": train_counts,
            "test_cluster_counts": test_counts,
            "train_cluster_ids": sorted(train[cluster_col].astype(str).unique().tolist()),
            "test_cluster_ids": sorted(test[cluster_col].astype(str).unique().tolist()),
            "heldout_itt_damage_change": ate, "heldout_itt_damage_change_95ci": ate_ci,
            "heldout_cate_policy_damage_change": policy_effect,
            "heldout_cate_policy_damage_change_95ci": policy_ci,
            "heldout_policy_treatment_share": float(np.mean(policy_choose_treatment)),
            "eligible_for_ranking": eligible,
            "status_reason": (
                "Held-out cluster-level ITT and learned policy intervals support lower damage; "
                "independent replication and external validation are still required."
                if eligible else
                "Held-out cluster-level evidence does not establish both average and policy benefit."
            ),
            "split_unit": cluster_col,
            "uncertainty_unit": cluster_col,
            "randomization_preserved": True,
            "compliance_analysis": "Not estimated; assigned arm is used for ITT.",
            "limitations": [
                "CATE is exploratory and may be unstable with few randomized clusters.",
                "No interference and consistent outcome measurement are still assumptions.",
                "Transport to Kochi or other hazards is not established.",
                "A randomized timing contrast does not identify effects of unrelated physical precautions.",
                "No independent replication or prospective deployment validation is included.",
            ],
        },
    )
