"""Scientific and fail-closed tests for intervention-effect ML."""
from __future__ import annotations

import pandas as pd
import pytest

from src.intervention_effectiveness import (
    InterventionDataError,
    rank_interventions,
    train_intervention_model,
    validate_intervention_frame,
)


def _small_frame(n: int = 80) -> pd.DataFrame:
    dates = pd.date_range("2010-01-01", periods=n, freq="D")
    return pd.DataFrame({
        "episode_date": dates,
        "outcome_window_end": dates + pd.Timedelta(days=1),
        "site_id": [f"site-{i % 8}" for i in range(n)],
        "hazard": ["Flood"] * n,
        "action_id": ["drain_maintenance"] * n,
        "implemented": [i % 2 for i in range(n)],
        "damage_outcome": [float(i % 7) for i in range(n)],
        "rainfall_before": [float(i % 15) for i in range(n)],
        "exposure_before": [float((i % 5) + 1) for i in range(n)],
    })


def test_intervention_schema_accepts_pre_treatment_covariates():
    features = validate_intervention_frame(_small_frame())
    assert features == ["rainfall_before", "exposure_before"]


@pytest.mark.parametrize("bad_column", [
    "damage_after", "future_rainfall", "post_treatment_repair_cost",
    "treatment_assignment_source",
])
def test_intervention_schema_rejects_post_treatment_or_treatment_leakage(bad_column):
    frame = _small_frame()
    frame[bad_column] = 1.0
    with pytest.raises(InterventionDataError):
        validate_intervention_frame(frame)


def test_intervention_training_fails_closed_when_sample_is_too_small():
    model = train_intervention_model(
        _small_frame(), action_id="drain_maintenance", hazard="Flood",
        test_start="2012-01-01",
    )
    assert model.status == "INSUFFICIENT_INTERVENTION_EVIDENCE"
    assert model.card["eligible_for_ranking"] is False
    assert model.estimate({"rainfall_before": 2, "exposure_before": 1})["available"] is False


def test_ranking_withholds_when_no_action_model_is_eligible():
    model = train_intervention_model(
        _small_frame(), action_id="drain_maintenance", hazard="Flood",
        test_start="2012-01-01",
    )
    result = rank_interventions([model], {"rainfall_before": 2, "exposure_before": 1})
    assert result["status"] == "RANKING_WITHHELD"
    assert result["ranked_actions"] == []


def test_prevention_catalogue_emits_stable_action_identifiers():
    from src.prevention_intelligence import generate_prevention_actions

    first = generate_prevention_actions(["Flood"])
    second = generate_prevention_actions(["Flood"])
    assert first and all(item.get("action_id") for item in first)
    assert [item["action_id"] for item in first] == [item["action_id"] for item in second]
    assert len({item["action_id"] for item in first}) == len(first)


def test_intervention_schema_rejects_duplicate_site_time_action_episodes():
    frame = _small_frame()
    frame = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)
    with pytest.raises(InterventionDataError, match="Duplicate"):
        validate_intervention_frame(frame)
