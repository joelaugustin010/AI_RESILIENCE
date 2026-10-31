"""Tests for provenance-checked Eloor monthly report loading and comparison."""

import json
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from src.air_quality_monthly_reports import (
    MonthlyReportError,
    compare_monthly_report_values,
    load_eloor_monthly_report,
    monthly_report_coverage,
)


ROOT = Path(__file__).resolve().parent
REPORTS = ROOT / "data" / "processed" / "air_quality"


class EloorMonthlyReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.august = load_eloor_monthly_report(REPORTS, "2026-08")
        cls.september = load_eloor_monthly_report(REPORTS, "2026-09")

    def test_loads_both_reports_with_source_dates_units_and_validation(self):
        self.assertEqual(len(self.august["observations"]), 279)
        self.assertEqual(len(self.september["observations"]), 270)
        self.assertEqual(self.august["expected_days"], 31)
        self.assertEqual(self.september["expected_days"], 30)
        self.assertEqual(self.september["observations"]["observed_at"].iloc[0], "2026-09-01")
        self.assertEqual(set(self.september["observations"]["unit"]), {"ug/m3", "mg/m3"})
        self.assertEqual(set(self.september["validated_observations"]["timestamp_precision"]), {"day"})
        self.assertIn("kspcb.kerala.gov.in", self.september["source_url"])
        self.assertEqual(set(self.september["observations"]["quality_flag"]), {"unassessed"})

    def test_monthly_coverage_counts_source_rows_without_filling_missing_dates(self):
        complete = monthly_report_coverage(self.september)
        self.assertEqual(len(complete), 11)
        self.assertEqual(set(complete["Missing dates"]), {0})
        self.assertEqual(set(complete["Missing value cells"]), {0})

        incomplete_report = dict(self.september)
        incomplete_report["observations"] = self.september["observations"].drop(index=0).copy()
        coverage = monthly_report_coverage(incomplete_report)
        pm10 = coverage.loc[coverage["Series"].eq("PM10")].iloc[0]
        self.assertEqual(pm10["Dates with records"], 29)
        self.assertEqual(pm10["Missing dates"], 1)
        self.assertEqual(pm10["Missing value cells"], 0)

        incomplete_report["aqi"] = self.september["aqi"].drop(index=0).copy()
        incomplete_report["weather"] = self.september["weather"].copy()
        incomplete_report["weather"].loc[incomplete_report["weather"].index[0], "temperature"] = pd.NA
        coverage = monthly_report_coverage(incomplete_report)
        aqi = coverage.loc[coverage["Series"].eq("Source AQI")].iloc[0]
        weather = coverage.loc[coverage["Series"].eq("Daily weather summary")].iloc[0]
        self.assertEqual(aqi["Missing dates"], 1)
        self.assertEqual(weather["Missing value cells"], 1)
        self.assertEqual(weather["Dates with values"], 29)

    def test_comparison_uses_only_shared_fields_with_identical_source_units_and_period_labels(self):
        comparison = compare_monthly_report_values([self.september, self.august])
        self.assertEqual(len(comparison), 9)
        self.assertEqual(set(comparison["Pollutant"]), {"PM10", "PM2.5", "SO2", "CO", "NO", "NO2", "NOx", "NH3", "O3"})
        self.assertTrue(comparison["Source averaging-period label"].str.contains("exact interval not stated").all())
        self.assertEqual(set(comparison["August 2026 dated values"]), {31})
        self.assertEqual(set(comparison["September 2026 dated values"]), {30})
        pm10 = comparison.loc[comparison["Pollutant"].eq("PM10")].iloc[0]
        self.assertEqual(pm10["Unit"], "ug/m3")
        self.assertAlmostEqual(
            pm10["August 2026 mean of daily report values"],
            self.august["observations"].loc[
                self.august["observations"]["pollutant"].eq("PM10"), "value"
            ].mean(),
        )
        self.assertAlmostEqual(
            pm10["September 2026 mean of daily report values"],
            self.september["observations"].loc[
                self.september["observations"]["pollutant"].eq("PM10"), "value"
            ].mean(),
        )

        first = dict(self.august)
        second = dict(self.september)
        first["observations"] = pd.DataFrame(
            [
                {"station": "Eloor", "pollutant": "PM10", "unit": "ug/m3", "averaging_period": "daily report value", "observed_at": "2026-08-01", "value": 20},
                {"station": "Eloor", "pollutant": "PM2.5", "unit": "ug/m3", "averaging_period": "daily report value", "observed_at": "2026-08-01", "value": 10},
            ]
        )
        second["observations"] = pd.DataFrame(
            [
                {"station": "Eloor", "pollutant": "PM10", "unit": "mg/m3", "averaging_period": "daily report value", "observed_at": "2026-09-01", "value": 0.02},
                {"station": "Eloor", "pollutant": "PM2.5", "unit": "ug/m3", "averaging_period": "hourly", "observed_at": "2026-09-01", "value": 11},
            ]
        )
        self.assertTrue(compare_monthly_report_values([first, second]).empty)

    def test_invalid_or_future_retrieval_dates_fail_provenance_checks(self):
        metadata_path = REPORTS / "kspcb_caaqms_eloor_2026-09.metadata.json"
        original_read_text = Path.read_text

        def load_with_retrieval_date(value):
            def altered_read_text(path: Path, *args, **kwargs):
                content = original_read_text(path, *args, **kwargs)
                if path == metadata_path:
                    metadata = json.loads(content)
                    metadata["sources"]["kspcb_caaqms_eloor_2026_09"]["retrieved_on"] = value
                    return json.dumps(metadata)
                return content
            return altered_read_text

        for retrieval_date in ("not-a-date", (date.today() + timedelta(days=1)).isoformat()):
            with self.subTest(retrieval_date=retrieval_date):
                with patch.object(Path, "read_text", load_with_retrieval_date(retrieval_date)):
                    with self.assertRaisesRegex(MonthlyReportError, "retrieval date"):
                        load_eloor_monthly_report(REPORTS, "2026-09")

    def test_modified_csv_fails_its_provenance_hash_check(self):
        daily_path = REPORTS / "kspcb_caaqms_eloor_daily_2026-09.csv"
        original_read_bytes = Path.read_bytes

        def altered_daily_bytes(path: Path) -> bytes:
            data = original_read_bytes(path)
            return data + b"\n" if path == daily_path else data

        with patch.object(Path, "read_bytes", altered_daily_bytes):
            with self.assertRaisesRegex(MonthlyReportError, "SHA-256"):
                load_eloor_monthly_report(REPORTS, "2026-09")


if __name__ == "__main__":
    unittest.main()
