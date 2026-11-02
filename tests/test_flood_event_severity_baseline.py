"""Governance and feature-timing tests for the INDOFLOODS research baseline."""
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.train_flood_event_severity_baseline import (
    filter_open_gauges,
    load_training_table,
    select_catchment_features,
)


class FloodSeverityBaselineTests(unittest.TestCase):
    def test_only_explicitly_open_gauges_are_eligible(self):
        metadata = pd.DataFrame({
            "GaugeID": ["open", "restricted", "unknown"],
            "Privacy": ["Open", "Restricted", None],
        })
        result = filter_open_gauges(metadata)
        self.assertEqual(result["GaugeID"].tolist(), ["open"])

    def test_missing_privacy_field_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "Privacy"):
            filter_open_gauges(pd.DataFrame({"GaugeID": ["g1"]}))

    def test_event_rainfall_windows_are_not_selected_as_features(self):
        frame = pd.DataFrame(columns=[
            "T1d", "T10d", "Drainage Area", "Catchment Relief",
            "Catchment Length", "Catchment Perimeter", "Drainage Density",
            "Land cover",
        ])
        numeric, categorical = select_catchment_features(frame)
        self.assertNotIn("T1d", numeric)
        self.assertNotIn("T10d", numeric)
        self.assertIn("Drainage Area", numeric)
        self.assertIn("Land cover", categorical)

    def test_training_table_excludes_restricted_gauge_events(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pd.DataFrame([
                {"EventID": "INDOFLOODS-gauge-1-1", "Peak Flood Level (m)": 2.0},
                {"EventID": "INDOFLOODS-gauge-2-1", "Peak Flood Level (m)": 0.5},
            ]).to_csv(root / "floodevents_indofloods.csv", index=False)
            pd.DataFrame([
                {"GaugeID": "INDOFLOODS-gauge-1", "Privacy": "Open", "Warning Level": 1.0, "Danger Level": 1.5, "Station": "A", "State": "Kerala"},
                {"GaugeID": "INDOFLOODS-gauge-2", "Privacy": "Restricted", "Warning Level": 1.0, "Danger Level": 1.5, "Station": "B", "State": "Kerala"},
            ]).to_csv(root / "metadata_indofloods.csv", index=False)
            pd.DataFrame([
                {"GaugeID": "INDOFLOODS-gauge-1", "Drainage Area": 100},
                {"GaugeID": "INDOFLOODS-gauge-2", "Drainage Area": 200},
            ]).to_csv(root / "catchment_characteristics_indofloods.csv", index=False)
            table = load_training_table(root)
            self.assertEqual(table["GaugeID"].unique().tolist(), ["INDOFLOODS-gauge-1"])
            self.assertEqual(len(table), 1)


if __name__ == "__main__":
    unittest.main()
