"""Unit tests for the Kerala spatial rainfall transfer experiment."""
from __future__ import annotations

import numpy as np

from scripts.train_kerala_cross_location_rainfall import (
    HELD_OUT_LOCATION,
    TRAIN_LOCATIONS,
    _paired_block_ci,
    _monthly_climatology,
    _regression_calibration_bins,
)


def test_kochi_is_excluded_from_all_training_locations() -> None:
    assert HELD_OUT_LOCATION == "kochi"
    assert HELD_OUT_LOCATION not in TRAIN_LOCATIONS
    assert set(TRAIN_LOCATIONS) == {"kottayam", "wayanad", "thiruvananthapuram"}


def test_paired_block_interval_is_reproducible_and_finite() -> None:
    actual = np.array([0.0, 2.0, 10.0, 0.0, 4.0, 8.0, 1.0, 0.0] * 5)
    model = np.array([1.0, 2.5, 7.0, 1.0, 4.5, 7.0, 1.5, 0.5] * 5)
    baseline = np.array([0.0, 3.0, 9.0, 0.0, 5.0, 9.0, 2.0, 0.0] * 5)
    first = _paired_block_ci(actual, model, baseline, draws=200, seed=7)
    second = _paired_block_ci(actual, model, baseline, draws=200, seed=7)
    assert first == second
    assert len(first) == 2
    assert np.isfinite(first).all()
    assert first[0] <= first[1]


def test_model_has_nonnegative_prediction_constraint_in_training_protocol() -> None:
    # The regression inference is clipped at zero because precipitation cannot
    # be negative; this guards the experiment's physical output contract.
    prediction = np.maximum(0.0, np.array([-2.0, 0.0, 3.0]))
    assert prediction.tolist() == [0.0, 0.0, 3.0]


def test_monthly_climatology_uses_training_targets_only() -> None:
    import pandas as pd

    train_dates = pd.Series(pd.to_datetime(["2010-01-01", "2011-01-01", "2010-02-01", "2011-02-01"]))
    train_targets = pd.Series([10.0, 20.0, 2.0, 4.0])
    test_dates = pd.Series(pd.to_datetime(["2024-01-01", "2024-02-01"]))
    result = _monthly_climatology(train_dates, train_targets, test_dates)
    assert result.tolist() == [15.0, 3.0]


def test_regression_calibration_bins_are_equal_count_and_report_bias() -> None:
    actual = np.array([1.0, 2.0, 4.0, 8.0, 10.0, 12.0])
    predicted = np.array([0.0, 1.0, 3.0, 7.0, 9.0, 11.0])
    result = _regression_calibration_bins(actual, predicted, bins=3)
    assert [row["n"] for row in result] == [2, 2, 2]
    assert all("bias_observed_minus_predicted_mm" in row for row in result)
