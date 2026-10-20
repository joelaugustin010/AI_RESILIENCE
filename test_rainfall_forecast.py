"""Tests for the out-of-time manual rainfall benchmark.

Synthetic observations below are controlled in-memory test fixtures. The
separate real-data test reads, but does not modify, the project's raw CSV.
"""

import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from src.rainfall_forecast import (
    RainfallForecastError,
    evaluate_hourly_rainfall,
    run_manual_rainfall_backtest,
)


ROOT = Path(__file__).resolve().parent


def synthetic_hourly_observations(days: int = 90) -> pd.DataFrame:
    times = pd.date_range("2020-01-01", periods=days * 24, freq="h")
    rows = []
    for station_number, station in enumerate(("Fixture A", "Fixture B")):
        for index, timestamp in enumerate(times):
            # Deterministic positive amounts; this fixture is not real rainfall.
            value = 1.0 + station_number + (index % 24) / 24 + (index % 7) / 14
            rows.append({"timestamp": timestamp, "station": station, "value": value})
    return pd.DataFrame(rows)


class RainfallForecastValidationTests(unittest.TestCase):
    def test_chronological_holdout_uses_only_exact_one_hour_pairs(self):
        observations = synthetic_hourly_observations()
        # Remove one observation to create a 2-hour interval; it must not be
        # silently interpolated into an hourly training or test example.
        observations = observations.loc[
            ~(
                observations["station"].eq("Fixture A")
                & observations["timestamp"].eq(pd.Timestamp("2020-02-20 12:00"))
            )
        ].reset_index(drop=True)

        result = evaluate_hourly_rainfall(observations)
        summary = result["summary"]
        predictions = result["predictions"]

        self.assertGreater(summary["train_pairs"], 20)
        self.assertGreater(summary["test_pairs"], 0)
        self.assertLess(summary["train_end_exclusive"], summary["test_start"])
        self.assertTrue((predictions["timestamp"] >= pd.Timestamp(summary["test_start"])).all())
        self.assertTrue(
            (
                predictions["timestamp"] - predictions["previous_timestamp"]
                == pd.Timedelta(hours=1)
            ).all()
        )
        self.assertEqual(result["metrics"]["gradient_boosting"]["n"], len(predictions))
        self.assertEqual(result["metrics"]["station_median"]["n"], len(predictions))

    def test_duplicate_station_time_is_rejected_without_deduplication(self):
        observations = synthetic_hourly_observations(days=30)
        observations = pd.concat([observations, observations.iloc[[0]]], ignore_index=True)
        with self.assertRaisesRegex(RainfallForecastError, "Duplicate station-time"):
            evaluate_hourly_rainfall(observations)

    def test_invalid_values_and_insufficient_series_are_rejected(self):
        observations = synthetic_hourly_observations(days=30)
        observations.loc[0, "value"] = -1
        with self.assertRaisesRegex(RainfallForecastError, "Negative rainfall"):
            evaluate_hourly_rainfall(observations)

        with self.assertRaisesRegex(RainfallForecastError, "Missing required"):
            evaluate_hourly_rainfall(pd.DataFrame({"timestamp": [], "value": []}))

        short = synthetic_hourly_observations(days=1)
        with self.assertRaises(RainfallForecastError):
            evaluate_hourly_rainfall(short)

    def test_real_manual_rainfall_backtest_reports_measured_results_and_gaps(self):
        result = run_manual_rainfall_backtest(ROOT)
        summary = result["summary"]
        self.assertEqual(summary["source_rows"], 109_978)
        self.assertEqual(summary["train_pairs"], 46_621)
        self.assertEqual(summary["test_pairs"], 11_675)
        self.assertEqual(summary["test_stations"], 15)
        self.assertEqual(summary["all_stations"], 21)
        self.assertTrue(summary["all_values_positive"])
        self.assertAlmostEqual(result["metrics"]["gradient_boosting"]["mae_mm"], 3.0221, places=3)
        self.assertAlmostEqual(result["metrics"]["station_median"]["mae_mm"], 3.0902, places=3)
        self.assertAlmostEqual(result["metrics"]["persistence"]["mae_mm"], 3.9594, places=3)
        self.assertTrue(any("flood forecast" in warning.lower() for warning in result["warnings"]))


if __name__ == "__main__":
    unittest.main()
