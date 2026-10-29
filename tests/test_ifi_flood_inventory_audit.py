"""Tests for the IFI descriptive audit; no real flood labels are synthesized."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.audit_ifi_flood_inventory import audit_csv, build_report


class IFIAuditTests(unittest.TestCase):
    def test_inventory_audit_reports_ernakulam_mentions_as_context_only(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "India_Flood_Inventory_v3.csv"
            pd.DataFrame([
                {
                    "UEI": "E1", "Start Date": "01-08-2018 00:00", "End Date": "10-08-2018 00:00",
                    "State": "Kerala", "Districts": "Ernakulam, Alappuzha",
                    "Latitude": None, "Longitude": None,
                },
                {
                    "UEI": "E2", "Start Date": "bad-date", "End Date": "12-08-2018 00:00",
                    "State": "Kerala", "Districts": "Idukki",
                    "Latitude": 10.0, "Longitude": 76.0,
                },
            ]).to_csv(path, index=False)
            report = audit_csv(path, "test_inventory")
            self.assertEqual(report["rows"], 2)
            self.assertEqual(report["rows_mentioning_both_kerala_and_ernakulam"], 1)
            self.assertEqual(report["start_date_invalid_count"], 1)
            self.assertIn("not an hourly station outcome", report["interpretation_warning"])

    def test_report_lists_missing_files_instead_of_inventing_data(self):
        with tempfile.TemporaryDirectory() as folder:
            report = build_report(Path(folder))
            self.assertEqual(len(report["datasets"]), 0)
            self.assertEqual(len(report["missing_expected_files"]), 4)
            self.assertIn("Do not convert district mentions", report["scientific_conclusion"])


if __name__ == "__main__":
    unittest.main()
