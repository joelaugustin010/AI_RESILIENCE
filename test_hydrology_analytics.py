"""Tests for source-preserving hydrology summaries and chart preparation."""

import json
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from src.hydrology_analytics import (
    DATASETS,
    HydrologyDataError,
    filter_observations,
    load_observations,
    rainfall_station_comparison,
    station_gap_summary,
)


ROOT = Path(__file__).resolve().parent


class HydrologyAnalyticsTests(unittest.TestCase):
    def test_real_rainfall_observations_load_and_manual_comparison_is_descriptive(self):
        observations, qa = load_observations("rainfall_manual", ROOT)
        self.assertGreater(qa["raw_rows"], 100_000)
        self.assertEqual(qa["invalid_timestamp_rows"], 0)
        self.assertEqual(qa["invalid_measurement_rows"], 0)
        self.assertEqual(qa["duplicate_station_time_groups"], 0)
        comparison = rainfall_station_comparison(observations)
        self.assertEqual(len(comparison), qa["station_count"])
        self.assertIn("95th percentile (mm)", comparison.columns)
        self.assertTrue((comparison["Maximum (mm)"] >= comparison["Median (mm)"]).all())

    def test_real_cwc_duplicate_groups_are_reported_not_removed_or_aggregated(self):
        observations, qa = load_observations("rainfall_cwc", ROOT)
        self.assertEqual(qa["raw_rows"], 9_206)
        self.assertEqual(qa["duplicate_station_time_groups"], 1_471)
        self.assertEqual(qa["conflicting_station_time_groups"], 324)
        self.assertEqual(len(observations), qa["valid_rows"])
        self.assertEqual(qa["valid_rows"], 9_206)

    def test_river_data_are_observational_and_keep_known_manantavadi_rows(self):
        for dataset_id in ("river_manual", "river_telemetry"):
            observations, qa = load_observations(dataset_id, ROOT)
            self.assertGreater(qa["station_count"], 1)
            self.assertIn("F.C.S. Mananthavadi", set(observations["station"]))
            self.assertEqual(DATASETS[dataset_id].unit, "m")
            self.assertIn("reference", DATASETS[dataset_id].warning.lower())
            self.assertIn("spatial attribution", DATASETS[dataset_id].warning.lower())

    def test_source_register_has_provenance_units_reuse_and_limitations(self):
        path = ROOT / "data" / "reference" / "hydrology_data_sources.json"
        register = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(len(register["datasets"]), 4)
        for source in register["datasets"]:
            self.assertTrue(source["source_url"].startswith("https://"))
            self.assertIn("license", source)
            self.assertIn("measurement", source)
            self.assertIn("observed_local_period", source)
            self.assertIn("geographic_coverage", source)
            self.assertIn("coordinate_reference_system", source)
            self.assertTrue(source["limitations"])
        self.assertIn("Other (Open)", register["reuse_policy"])

    def test_filter_is_inclusive_and_gap_is_an_observed_interval_not_missing_count(self):
        frame = pd.DataFrame({
            "timestamp": pd.to_datetime(["2021-10-12 00:00", "2021-10-12 01:00", "2021-10-14 01:00"]),
            "station": ["S"] * 3,
            "value": [1.0, 2.0, 3.0],
        })
        selected = filter_observations(frame, "S", "2021-10-12", "2021-10-12")
        self.assertEqual(len(selected), 2)
        gap = station_gap_summary(frame)
        self.assertEqual(gap["unique_timestamps"], 3)
        self.assertEqual(gap["maximum_observed_gap_hours"], 48.0)

    def test_invalid_columns_unknown_dataset_and_conflicting_fixture_are_handled(self):
        with self.assertRaises(HydrologyDataError):
            load_observations("not-a-dataset", ROOT)
        temporary_root = ROOT / "test_fixture_root"
        with patch("src.hydrology_analytics.pd.read_csv", return_value=pd.DataFrame({"Station": ["X"]})):
            with self.assertRaisesRegex(HydrologyDataError, "Missing required"):
                load_observations("rainfall_cwc", temporary_root)

            # This controlled test fixture is not stored or described as real data.
            fixture = pd.DataFrame({
                "Station": ["Test", "Test"],
                "Data Acquisition Time": ["01-10-2021 01:00", "01-10-2021 01:00"],
                "Telemetry Hourly Rainfall (mm)": [1.0, 2.0],
            })
            with patch("src.hydrology_analytics.pd.read_csv", return_value=fixture):
                observations, qa = load_observations("rainfall_cwc", temporary_root)
            self.assertEqual(len(observations), 2)
            self.assertEqual(qa["duplicate_station_time_groups"], 1)
            self.assertEqual(qa["conflicting_station_time_groups"], 1)

    def test_event_context_has_provenance_and_does_not_claim_sensor_outcomes(self):
        path = ROOT / "data" / "reference" / "historical_flood_events.json"
        events = json.loads(path.read_text(encoding="utf-8"))["events"]
        self.assertEqual({event["event_id"] for event in events}, {
            "kerala_floods_2018", "kerala_flood_landslide_2021"
        })
        for event in events:
            self.assertTrue(event["source_url"].startswith("https://"))
            self.assertIn("context", event["relationship_to_local_observations"].lower())
        self.assertIn("not a model label", events[1]["relationship_to_local_observations"].lower())


if __name__ == "__main__":
    unittest.main()
