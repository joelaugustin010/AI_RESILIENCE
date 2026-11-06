"""Tests for cluster-randomized multi-arm trial analysis."""
import numpy as np
import pandas as pd
import pytest

from src.randomized_intervention_trials import (
    TrialDataError, fit_randomized_contrast, validate_trial_frame,
)


def _trial_frame(seed=7):
    rng = np.random.default_rng(seed)
    rows = []
    for cluster in range(36):
        arm = ("early" if cluster % 3 == 0 else
               "rapid" if cluster % 3 == 1 else "standard")
        for household in range(12):
            risk = float(rng.normal())
            effect = -0.8 if arm == "early" else (-0.2 if arm == "rapid" else 0.0)
            rows.append({
                "episode_id": f"v{cluster}-h{household}",
                "assignment_cluster_id": f"v{cluster}",
                "assigned_arm": arm,
                "baseline_risk": risk,
                "house_type": "weak" if household % 2 else "strong",
                "damage_outcome": 3.0 + risk + effect + rng.normal(0, 0.2),
            })
    return pd.DataFrame(rows)


def test_randomized_contrast_uses_whole_clusters_and_itt():
    frame = _trial_frame()
    model = fit_randomized_contrast(
        frame, treatment_arm="early", reference_arm="standard",
        assignment_probabilities={"early": 1/3, "rapid": 1/3, "standard": 1/3},
        feature_columns=["baseline_risk", "house_type"],
        outcome_unit="illustrative damage-severity units",
        min_clusters_per_arm=8, seed=19,
    )
    report = model.report
    assert report["randomization_preserved"] is True
    assert report["estimand"].startswith("Intention-to-treat")
    assert set(report["train_cluster_counts"]).isdisjoint(
        set(report["test_cluster_counts"])
    )
    assert report["test_cluster_counts"]["early"] >= 2
    assert report["test_cluster_counts"]["standard"] >= 2
    assert report["heldout_itt_damage_change"] < 0


def test_rejects_cluster_assigned_to_multiple_arms():
    frame = _trial_frame()
    frame.loc[1, "assigned_arm"] = "standard"
    with pytest.raises(TrialDataError, match="more than one assigned arm"):
        validate_trial_frame(
            frame, ["baseline_risk", "house_type"]
        )


def test_rejects_asset_level_pseudoreplication_duplicate_episode_ids():
    frame = _trial_frame()
    frame.loc[1, "episode_id"] = frame.loc[0, "episode_id"]
    with pytest.raises(TrialDataError, match="one aggregated observation"):
        validate_trial_frame(frame, ["baseline_risk", "house_type"])


def test_rejects_post_assignment_features():
    frame = _trial_frame()
    with pytest.raises(TrialDataError, match="leakage"):
        validate_trial_frame(frame, ["baseline_risk", "received_cash"])
