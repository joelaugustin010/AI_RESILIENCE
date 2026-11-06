"""Causal-ML research engine for comparing disaster-risk-reduction interventions.

Input rows must be real, linked intervention episodes. Each row represents one
site/time episode with a binary indicator for whether ONE named intervention
was implemented, a pre-intervention damage-severity outcome, and covariates
measured before treatment. Lower outcomes are better.

This is an observational doubly-robust learner, not proof of causality:
unmeasured confounding, treatment-version differences, spillovers and selection
bias remain possible. It fails closed when evidence/overlap is inadequate.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, ExtraTreesRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import mean_absolute_error


SCHEMA_VERSION = "intervention-effectiveness/0.1.0"
REQUIRED_COLUMNS = {
    "episode_date", "site_id", "hazard", "action_id", "implemented",
    "damage_outcome",
}
MIN_TOTAL_ROWS = 200
MIN_PER_ARM = 50
MIN_TEST_PER_ARM = 30
MIN_OVERLAP_SHARE = 0.80
PROPENSITY_CLIP = 0.05
FORBIDDEN_FEATURE_TOKENS = (
    "outcome", "damage_after", "loss_after", "future", "post_treatment",
    "implemented", "treatment", "action_id", "recovery_cost",
)


class InterventionDataError(ValueError):
    """Input intervention records are not fit for causal-effect estimation."""


@dataclass
class InterventionModel:
    action_id: str
    hazard: str
    feature_columns: list[str]
    preprocessor: Any
    effect_model: Any
    status: str
    card: dict[str, Any]

    def estimate(self, context: dict[str, Any]) -> dict[str, Any]:
        if self.status != "CAUSAL_RESEARCH_SIGNAL_NOT_VALIDATED":
            return {
                "action_id": self.action_id,
                "status": self.status,
                "available": False,
                "reason": "Intervention-effect evidence did not pass the research eligibility gates.",
            }
        missing = [name for name in self.feature_columns if name not in context]
        if missing:
            return {
                "action_id": self.action_id,
                "status": "CONTEXT_INCOMPLETE",
                "available": False,
                "missing_features": missing,
            }
        row = pd.DataFrame([{name: context[name] for name in self.feature_columns}])
        x = self.preprocessor.transform(row)
        reduction = -float(self.effect_model.predict(x)[0])
        return {
            "action_id": self.action_id,
            "hazard": self.hazard,
            "status": self.status,
            "available": True,
            "estimated_damage_reduction": reduction,
            "outcome_unit": self.card["outcome_unit"],
            "interpretation": (
                "Positive values indicate lower damage outcome under the intervention "
                "than under no intervention; this is an observational research estimate, "
                "not a guaranteed or independently validated effect."
            ),
            "model_card": self.card,
        }


def _feature_preprocessor(frame: pd.DataFrame, columns: list[str]) -> ColumnTransformer:
    numeric = [c for c in columns if pd.api.types.is_numeric_dtype(frame[c])]
    categorical = [c for c in columns if c not in numeric]
    transformers = []
    if numeric:
        transformers.append(("numeric", SimpleImputer(strategy="median"), numeric))
    if categorical:
        transformers.append((
            "categorical",
            Pipeline([
                ("imputer", SimpleImputer(strategy="most_frequent")),
                ("onehot", OneHotEncoder(handle_unknown="ignore")),
            ]),
            categorical,
        ))
    return ColumnTransformer(transformers, remainder="drop")


def _make_outcome_model(seed: int) -> RandomForestRegressor:
    return RandomForestRegressor(
        n_estimators=250, min_samples_leaf=8, max_features=0.8,
        random_state=seed, n_jobs=-1,
    )


def _make_propensity_model(seed: int) -> LogisticRegression:
    # Covariates have already passed through the shared preprocessor.
    return LogisticRegression(max_iter=2000, class_weight="balanced", random_state=seed)


def _crossfit_dr_score(
    x: np.ndarray, treatment: np.ndarray, outcome: np.ndarray,
    *, seed: int = 42, folds: int = 5,
) -> tuple[np.ndarray, np.ndarray]:
    """Cross-fit nuisance outcome/propensity models and form DR pseudo-outcomes."""
    rng = np.random.default_rng(seed)
    indices = rng.permutation(len(outcome))
    fold_ids = np.array_split(indices, min(folds, len(indices)))
    pseudo = np.full(len(outcome), np.nan, dtype=float)
    propensities = np.full(len(outcome), np.nan, dtype=float)
    for fold, held in enumerate(fold_ids):
        train = np.setdiff1d(np.arange(len(outcome)), held, assume_unique=False)
        if len(np.unique(treatment[train])) < 2:
            raise InterventionDataError("Cross-fitting fold lacks both treated and control episodes.")
        p_model = _make_propensity_model(seed + fold)
        p_model.fit(x[train], treatment[train])
        raw_propensity = p_model.predict_proba(x[held])[:, 1]
        propensity = np.clip(raw_propensity, PROPENSITY_CLIP, 1 - PROPENSITY_CLIP)
        m0, m1 = _make_outcome_model(seed + 100 + fold), _make_outcome_model(seed + 200 + fold)
        m0.fit(x[train][treatment[train] == 0], outcome[train][treatment[train] == 0])
        m1.fit(x[train][treatment[train] == 1], outcome[train][treatment[train] == 1])
        mu0, mu1 = m0.predict(x[held]), m1.predict(x[held])
        t, y = treatment[held], outcome[held]
        pseudo[held] = (mu1 - mu0) + t * (y - mu1) / propensity - (1 - t) * (y - mu0) / (1 - propensity)
        propensities[held] = raw_propensity
    return pseudo, propensities


def _bootstrap_mean_ci(values: np.ndarray, *, seed: int = 42, n_bootstrap: int = 2000) -> list[float]:
    values = np.asarray(values, dtype=float)
    if len(values) < 2:
        return [float("nan"), float("nan")]
    rng = np.random.default_rng(seed)
    samples = rng.integers(0, len(values), size=(n_bootstrap, len(values)))
    means = values[samples].mean(axis=1)
    return [float(v) for v in np.quantile(means, [0.025, 0.975])]


def validate_intervention_frame(
    frame: pd.DataFrame, *, feature_columns: Iterable[str] | None = None,
) -> list[str]:
    """Validate the observational episode schema and pre-treatment feature contract."""
    missing = sorted(REQUIRED_COLUMNS - set(frame.columns))
    if missing:
        raise InterventionDataError(f"Missing required columns: {missing}")
    if frame.empty:
        raise InterventionDataError("No intervention episodes supplied.")
    if frame["episode_date"].isna().any() or pd.to_datetime(frame["episode_date"], errors="coerce").isna().any():
        raise InterventionDataError("episode_date must contain valid dates.")
    if frame["site_id"].isna().any() or frame["action_id"].isna().any() or frame["hazard"].isna().any():
        raise InterventionDataError("site_id, hazard and action_id cannot be blank.")
    if not set(pd.to_numeric(frame["implemented"], errors="coerce").dropna().unique()).issubset({0, 1}):
        raise InterventionDataError("implemented must be binary 0/1.")
    if frame["implemented"].isna().any():
        raise InterventionDataError("implemented contains missing values.")
    if not pd.to_numeric(frame["damage_outcome"], errors="coerce").notna().all():
        raise InterventionDataError("damage_outcome must be numeric and complete.")
    excluded = REQUIRED_COLUMNS | {"outcome_unit"}
    inferred = list(feature_columns) if feature_columns is not None else [
        c for c in frame.columns if c not in excluded
    ]
    if not inferred:
        raise InterventionDataError("At least one pre-intervention covariate is required.")
    bad = [c for c in inferred if any(token in c.lower() for token in FORBIDDEN_FEATURE_TOKENS)]
    if bad:
        raise InterventionDataError(f"Post-treatment or treatment-identifying features are forbidden: {bad}")
    absent = [c for c in inferred if c not in frame.columns]
    if absent:
        raise InterventionDataError(f"Feature columns not found: {absent}")
    if frame[inferred].isna().all(axis=1).mean() > 0.20:
        raise InterventionDataError("More than 20% of episodes have no observed covariates.")
    return inferred


def train_intervention_model(
    frame: pd.DataFrame, *, action_id: str, hazard: str,
    feature_columns: Iterable[str] | None = None,
    outcome_unit: str = "normalised damage-severity units",
    test_start: str | pd.Timestamp = "2022-01-01",
    seed: int = 42,
) -> InterventionModel:
    """Fit a time-held-out doubly-robust CATE model for one action vs no action.

    Outcome is coded so lower is better. Only pre-intervention covariates may
    be supplied. A positive reported reduction means lower expected damage.
    """
    features = validate_intervention_frame(frame, feature_columns=feature_columns)
    data = frame.loc[(frame["hazard"].astype(str) == hazard) & (frame["action_id"].astype(str) == action_id)].copy()
    data["episode_date"] = pd.to_datetime(data["episode_date"])
    data["implemented"] = data["implemented"].astype(int)
    data["damage_outcome"] = pd.to_numeric(data["damage_outcome"], errors="raise")
    cutoff = pd.Timestamp(test_start)
    train = data.loc[data["episode_date"] < cutoff].copy()
    test = data.loc[data["episode_date"] >= cutoff].copy()

    counts = {
        "total": int(len(data)),
        "train_treated": int((train["implemented"] == 1).sum()),
        "train_control": int((train["implemented"] == 0).sum()),
        "test_treated": int((test["implemented"] == 1).sum()),
        "test_control": int((test["implemented"] == 0).sum()),
    }
    base_card = {
        "schema_version": SCHEMA_VERSION, "action_id": action_id, "hazard": hazard,
        "outcome": "damage_outcome (lower is better)", "outcome_unit": outcome_unit,
        "feature_columns": features, "counts": counts, "test_start": cutoff.date().isoformat(),
        "causal_estimand": "Conditional average treatment effect: intervention minus no intervention.",
        "assumptions": [
            "Consistency and a well-defined intervention version.",
            "Conditional exchangeability given measured pre-intervention covariates (untestable).",
            "Positivity / treatment overlap in the target population.",
            "No interference between site-time episodes (may be violated by networked hazards).",
            "No material outcome measurement differences by treatment status.",
        ],
        "limitations": [
            "Observational estimates can be confounded by unmeasured factors.",
            "Intervention delivery, quality, timing and compliance may vary.",
            "Effects may not transport to a different district, hazard intensity or population.",
            "A single chronological holdout is preliminary, not independent validation.",
        ],
    }

    def blocked(reason: str, status: str = "INSUFFICIENT_INTERVENTION_EVIDENCE") -> InterventionModel:
        card = {**base_card, "status": status, "status_reason": reason, "eligible_for_ranking": False}
        return InterventionModel(action_id, hazard, features, None, None, status, card)

    if len(train) < MIN_TOTAL_ROWS or counts["train_treated"] < MIN_PER_ARM or counts["train_control"] < MIN_PER_ARM:
        return blocked(f"Training requires at least {MIN_TOTAL_ROWS} episodes and {MIN_PER_ARM} in each arm; observed {counts}.")
    if counts["test_treated"] < MIN_TEST_PER_ARM or counts["test_control"] < MIN_TEST_PER_ARM:
        return blocked(f"Chronological test requires at least {MIN_TEST_PER_ARM} treated and control episodes; observed {counts}.")

    preprocessor = _feature_preprocessor(train, features)
    x_train = preprocessor.fit_transform(train[features])
    x_test = preprocessor.transform(test[features])
    t_train = train["implemented"].to_numpy(dtype=int)
    y_train = train["damage_outcome"].to_numpy(dtype=float)
    t_test = test["implemented"].to_numpy(dtype=int)
    y_test = test["damage_outcome"].to_numpy(dtype=float)

    pseudo_train, propensity_train = _crossfit_dr_score(x_train, t_train, y_train, seed=seed)
    overlap_train = (propensity_train >= PROPENSITY_CLIP) & (propensity_train <= 1 - PROPENSITY_CLIP)
    overlap_share = float(overlap_train.mean())
    if overlap_share < MIN_OVERLAP_SHARE:
        return blocked(f"Treatment overlap coverage {overlap_share:.3f} is below {MIN_OVERLAP_SHARE:.2f}; do not extrapolate.")
    effect_model = ExtraTreesRegressor(
        n_estimators=300, min_samples_leaf=12, max_features=0.8,
        random_state=seed, n_jobs=-1,
    )
    effect_model.fit(x_train, pseudo_train)

    # Held-out doubly-robust ATE: nuisance models are trained only on pre-test data.
    p_model = _make_propensity_model(seed + 500)
    p_model.fit(x_train, t_train)
    raw_p_test = p_model.predict_proba(x_test)[:, 1]
    p_test = np.clip(raw_p_test, PROPENSITY_CLIP, 1 - PROPENSITY_CLIP)
    m0, m1 = _make_outcome_model(seed + 501), _make_outcome_model(seed + 502)
    m0.fit(x_train[t_train == 0], y_train[t_train == 0])
    m1.fit(x_train[t_train == 1], y_train[t_train == 1])
    mu0, mu1 = m0.predict(x_test), m1.predict(x_test)
    dr_test = (mu1 - mu0) + t_test * (y_test - mu1) / p_test - (1 - t_test) * (y_test - mu0) / (1 - p_test)
    ci = _bootstrap_mean_ci(dr_test, seed=seed + 503)
    mean_effect = float(np.mean(dr_test))
    test_overlap = float(np.mean((raw_p_test >= PROPENSITY_CLIP) & (raw_p_test <= 1 - PROPENSITY_CLIP)))
    status = "CAUSAL_RESEARCH_SIGNAL_NOT_VALIDATED"
    eligible = bool(mean_effect < 0 and ci[1] < 0 and test_overlap >= MIN_OVERLAP_SHARE)
    if not eligible:
        status = "NO_CLEAR_HARM_REDUCTION_SIGNAL"
    card = {
        **base_card, "status": status,
        "status_reason": (
            "Held-out doubly-robust damage effect is below zero and its bootstrap 95% interval excludes zero; "
            "observational assumptions remain unverified."
            if eligible else
            "Held-out data do not establish a damage-reduction effect with adequate overlap."
        ),
        "metrics": {
            "heldout_dr_mean_effect": mean_effect,
            "heldout_dr_effect_95ci": ci,
            "heldout_overlap_share": test_overlap,
            "training_overlap_share": overlap_share,
            "heldout_mae_of_dr_score_vs_cate": float(mean_absolute_error(dr_test, effect_model.predict(x_test))),
            "outcome_mean_treated_test": float(np.mean(y_test[t_test == 1])),
            "outcome_mean_control_test": float(np.mean(y_test[t_test == 0])),
        },
        "eligible_for_ranking": eligible,
        "ranking_note": "Eligible actions may be ranked by context-specific estimated damage reduction only against actions trained on the same hazard, outcome scale and target population.",
    }
    return InterventionModel(action_id, hazard, features, preprocessor, effect_model, status, card)


def rank_interventions(
    models: Iterable[InterventionModel], context: dict[str, Any], *,
    max_actions: int = 5,
) -> dict[str, Any]:
    """Rank only research-eligible interventions; never fabricate fallback scores."""
    estimates = []
    excluded = []
    for model in models:
        result = model.estimate(context)
        if result.get("available") and model.card.get("eligible_for_ranking"):
            estimates.append(result)
        else:
            excluded.append({
                "action_id": model.action_id,
                "status": result.get("status"),
                "reason": result.get("reason", model.card.get("status_reason")),
            })
    if not estimates:
        return {
            "status": "RANKING_WITHHELD",
            "ranked_actions": [],
            "excluded_actions": excluded,
            "reason": "No action has sufficient held-out observational evidence to support a comparative ranking.",
        }
    estimates.sort(key=lambda item: item["estimated_damage_reduction"], reverse=True)
    return {
        "status": "RESEARCH_RANKING_NOT_VALIDATED",
        "ranked_actions": estimates[:max_actions],
        "excluded_actions": excluded,
        "warning": (
            "This is a provisional observational ranking, not a causal guarantee or an instruction. "
            "Unmeasured confounding and site-specific engineering constraints may reverse the ranking. "
            "Official authorities and qualified professionals retain decision authority."
        ),
    }
