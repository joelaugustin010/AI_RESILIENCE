"""Tests for the read-only air-quality dataset readiness audit."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from src.air_quality_readiness import audit_air_quality_datasets


ROOT = Path(__file__).resolve().parent


class AirQualityReadinessAuditTests(unittest.TestCase):
    def test_repository_audit_separates_descriptive_data_from_forecasting(self):
        report = audit_air_quality_datasets(ROOT)
        datasets = {item["dataset_id"]: item for item in report["datasets"]}

        self.assertEqual(report["schema_version"], 1)
        self.assertFalse(report["forecasting_ready"])
        self.assertEqual(report["forecast_training_dataset_count"], 0)
        self.assertEqual(datasets["kspcb_annual_aqi"]["status"], "provisional")
        self.assertEqual(datasets["kspcb_daily_aqi_2026_10_16"]["status"], "provisional")
        self.assertEqual(datasets["kspcb_eloor_caaqms_2026_08"]["status"], "provisional")
        self.assertEqual(datasets["kspcb_eloor_caaqms_2026_09"]["status"], "provisional")
        self.assertEqual(datasets["kspcb_namp_ernakulam_2025_06"]["status"], "unsuitable")
        self.assertFalse(datasets["kspcb_namp_ernakulam_2025_06"]["descriptive_analysis_eligible"])
        self.assertEqual(datasets["cpcb_realtime_aqi"]["status"], "unavailable")
        self.assertEqual(datasets["kspcb_annual_aqi"]["integrity_check"], "passed")
        self.assertEqual(datasets["kspcb_annual_aqi"]["row_count"], 130)
        self.assertEqual(datasets["kspcb_eloor_caaqms_2026_09"]["row_count"], 270)
        self.assertEqual(datasets["kspcb_daily_aqi_station_status_2026_10_16"]["row_count"], 4)

    def test_corrupt_processed_csv_is_marked_unsuitable(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            air_dir = root / "data/processed/air_quality"
            air_dir.mkdir(parents=True)
            csv_path = air_dir / "kspcb_annual_aqi.csv"
            csv_path.write_text(
                "year,source_station,monitoring_mode,average_aqi\n2026,Eloor,NAMP,42\n",
                encoding="utf-8",
            )
            metadata = {
                "processed_sha256": hashlib.sha256(b"different bytes").hexdigest(),
                "rows": 1,
            }
            (air_dir / "kspcb_annual_aqi.metadata.json").write_text(
                json.dumps(metadata), encoding="utf-8"
            )
            (air_dir / "kspcb_air_reports.metadata.json").write_text(
                json.dumps({"sources": {}}), encoding="utf-8"
            )

            report = audit_air_quality_datasets(root)
            annual = next(
                item for item in report["datasets"]
                if item["dataset_id"] == "kspcb_annual_aqi"
            )
            self.assertEqual(annual["status"], "unsuitable")
            self.assertEqual(annual["integrity_check"], "failed")
            self.assertTrue(any("SHA-256" in error for error in annual["errors"]))

    def test_missing_local_air_data_is_reported_without_crashing_or_claiming_readiness(self):
        with tempfile.TemporaryDirectory() as temporary:
            report = audit_air_quality_datasets(Path(temporary))
            self.assertFalse(report["forecasting_ready"])
            self.assertEqual(report["status_counts"]["unavailable"], 7)
            self.assertTrue(report["catalog_errors"])
            self.assertTrue(
                all(
                    item["status"] in {"unavailable", "unsuitable"}
                    for item in report["datasets"]
                )
            )


if __name__ == "__main__":
    unittest.main()
