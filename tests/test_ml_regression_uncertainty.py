"""Regression forecast quality safeguards for dependent disaster observations."""

import numpy as np
import pytest

from src.ml.regression import _paired_mae_improvement_ci
from src.ml.inference import ModelNotUsableError, _apply_regression_constraints


def test_moving_block_bootstrap_is_reproducible_and_finite():
    actual = np.array([2.0, 4.0, 3.0, 8.0, 7.0, 9.0, 4.0, 3.0, 5.0, 6.0])
    model = actual + np.array([0.1, 0.2, 0.1, 0.3, 0.2, 0.1, 0.2, 0.1, 0.2, 0.1])
    baseline = actual + 1.0

    first = _paired_mae_improvement_ci(actual, model, baseline, block_length=3)
    second = _paired_mae_improvement_ci(actual, model, baseline, block_length=3)

    assert first == second
    assert np.isfinite(first).all()
    assert first[0] > 0


def test_storm_bootstrap_resamples_whole_groups_and_is_finite():
    actual = np.array([2.0, 3.0, 4.0, 8.0, 9.0, 10.0])
    model = actual + 0.1
    baseline = actual + 1.0
    storm_ids = np.array(["storm-a", "storm-a", "storm-a", "storm-b", "storm-b", "storm-b"])

    interval = _paired_mae_improvement_ci(
        actual, model, baseline, group_ids=storm_ids, n_bootstrap=300
    )

    assert np.isfinite(interval).all()
    assert interval[0] > 0


def test_group_bootstrap_rejects_missing_or_misaligned_storm_ids():
    values = np.array([1.0, 2.0, 3.0])

    with pytest.raises(ValueError, match="complete and match"):
        _paired_mae_improvement_ci(
            values, values, values + 1, group_ids=np.array(["storm-a", None, "storm-b"], dtype=object)
        )

    with pytest.raises(ValueError, match="complete and match"):
        _paired_mae_improvement_ci(
            values, values, values + 1, group_ids=np.array(["storm-a", "storm-b"])
        )


def test_block_bootstrap_rejects_invalid_block_length():
    values = np.array([1.0, 2.0, 3.0])

    with pytest.raises(ValueError, match="block_length"):
        _paired_mae_improvement_ci(values, values, values + 1, block_length=0)



def test_regression_inference_enforces_nonnegative_precipitation():
    value, constraints = _apply_regression_constraints(
        -3.5,
        {"prediction_constraints": {"lower_bound": 0.0}},
        "weather_precipitation_kochi_nextday_regression",
    )

    assert value == 0.0
    assert constraints == {"lower_bound": 0.0}


def test_regression_inference_rejects_invalid_physical_constraint():
    with pytest.raises(ModelNotUsableError, match="non-finite"):
        _apply_regression_constraints(
            2.0, {"prediction_constraints": {"lower_bound": float("nan")}}, "bad-model"
        )
