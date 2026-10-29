"""Tests for the descriptive INDOFLOODS audit; no predictive claims are tested."""
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.audit_indofloods import build_report


class IndofloodsAuditTests(unittest.TestCase):
    def write_table(self, root: Path, filename: str, frame: pd.DataFrame) -> None:
        frame.to_csv(root / filename, index=False)

    def test_kerala_gauge_events_are_crosswalked_by_explicit_gauge_id(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_table(root, "metadata_indofloods.csv", pd.DataFrame([
                {"GaugeID": "INDOFLOODS-gauge-429", "State": "Kerala", "Station": "Example", "Latitude": 9.22, "Longitude": 76.71, "Basin": "West flowing"},
                {"GaugeID": "INDOFLOODS-gauge-999", "State": "Other", "Station": "Other", "Latitude": 20, "Longitude": 80, "Basin": "Other"},
            ]))
            self.write_table(root, "floodevents_indofloods.csv", pd.DataFrame([
                {"EventID": "INDOFLOODS-gauge-429-1", "Start Date": "2018-08-01", "End Date": "2018-08-02"},
                {"EventID": "INDOFLOODS-gauge-999-1", "Start Date": "2018-08-01", "End Date": "2018-08-02"},
            ]))
            self.write_table(root, "catchment_characteristics_indofloods.csv", pd.DataFrame([
                {"GaugeID": "INDOFLOODS-gauge-429", "Drainage Area": 810},
            ]))
            self.write_table(root, "precipitation_variables_indofloods.csv", pd.DataFrame([
                {"EventID": "INDOFLOODS-gauge-429-1", "T1d": 10},
            ]))
            report = build_report(root)
            self.assertEqual(report["crosswalk_checks"]["kerala_gauge_count"], 1)
            self.assertEqual(report["crosswalk_checks"]["event_rows_for_kerala_gauges"], 1)
            self.assertEqual(report["crosswalk_checks"]["kerala_gauges_with_at_least_one_event"], ["INDOFLOODS-gauge-429"])
            self.assertEqual(report["missing_expected_files"], [])

    def test_missing_files_are_reported_not_fabricated(self):
        with tempfile.TemporaryDirectory() as directory:
            report = build_report(Path(directory))
            self.assertEqual(len(report["missing_expected_files"]), 4)
            self.assertEqual(report["crosswalk_checks"]["kerala_gauge_count"], None)

    def test_district_or_station_event_data_are_not_claimed_as_prediction(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_table(root, "metadata_indofloods.csv", pd.DataFrame([
                {"GaugeID": "INDOFLOODS-gauge-429", "State": "Kerala", "Station": "Example"},
            ]))
            self.write_table(root, "floodevents_indofloods.csv", pd.DataFrame([
                {"EventID": "INDOFLOODS-gauge-429-1", "Start Date": "2018-08-01", "End Date": "2018-08-02"},
            ]))
            self.write_table(root, "catchment_characteristics_indofloods.csv", pd.DataFrame([{"GaugeID": "INDOFLOODS-gauge-429"}]))
            self.write_table(root, "precipitation_variables_indofloods.csv", pd.DataFrame([{"EventID": "INDOFLOODS-gauge-429-1", "T1d": 10}]))
            report = build_report(root)
            self.assertIn("do not provide representative non-event examples", report["scientific_conclusion"])
            self.assertIn("not automatically a Kochi model dataset", report["scientific_conclusion"])


if __name__ == "__main__":
    unittest.main()
