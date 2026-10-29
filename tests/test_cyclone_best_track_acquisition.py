"""Unit tests for the IMD cyclone best-track acquisition and descriptive audit."""
from __future__ import annotations

import unittest

import pandas as pd

from scripts.acquire_cyclone_best_track import build_audit_report, haversine_km, validate_source_manifest


def sample_manifest():
    return {
        "source_url": "https://rsmcnewdelhi.imd.gov.in/download.php?path=uploads/best-track/test.xlsx",
        "source_sha256": "a" * 64,
        "generated_at": "2026-08-09T13:49:29+00:00",
        "n_storms": 2,
        "n_obs": 3,
        "n_remarks": 1,
        "year_min": 2024,
        "year_max": 2024,
    }


class CycloneBestTrackAuditTests(unittest.TestCase):
    def test_haversine_distance_is_zero_at_same_point(self):
        self.assertAlmostEqual(float(haversine_km([9.9312], [76.2673])[0]), 0.0, places=5)

    def test_audit_screens_non_suspect_tracks_and_preserves_flags(self):
        observations = pd.DataFrame({
            "storm_id": ["2024-001", "2024-001", "2024-002"],
            "time": ["2024-10-01T00:00:00Z", "2024-10-01T03:00:00Z", "2024-10-02T00:00:00Z"],
            "lat": [9.9312, 10.0, 20.0],
            "lon": [76.2673, 76.3, 80.0],
            "basin": ["ARB", "ARB", "BOB"],
            "year": [2024, 2024, 2024],
            "name": ["Sample A", "Sample A", "Sample B"],
            "wind": [20, 30, 40],
            "pos_suspect": [False, True, False],
            "date_suspect": [False, False, True],
        })
        storms = pd.DataFrame({"storm_id": ["2024-001", "2024-002"]})
        remarks = pd.DataFrame({"storm_id": ["2024-001"]})
        report = build_audit_report(observations, storms, remarks, sample_manifest(), {"observations.parquet": "b" * 64})
        self.assertEqual(report["data_quality"]["position_suspect_rows"], 1)
        self.assertEqual(report["data_quality"]["date_suspect_rows"], 1)
        self.assertEqual(report["kochi_proximity_screening"]["storms_with_at_least_one_non_suspect_fix_within_100_km"], 1)
        self.assertEqual(report["kochi_proximity_screening"]["storms_with_at_least_one_non_suspect_fix_within_300_km"], 1)
        self.assertEqual(report["kochi_proximity_screening"]["nearest_storms"][0]["storm_id"], "2024-001")
        self.assertEqual(report["status"], "DESCRIPTIVE_AUDIT_ONLY_NOT_VALIDATED_FOR_IMPACT_PREDICTION")

    def test_manifest_counts_must_match_downloaded_tables(self):
        observations = pd.DataFrame({
            "storm_id": ["a"], "time": ["2024-01-01T00:00:00Z"],
            "lat": [9.9], "lon": [76.2], "basin": ["ARB"], "year": [2024],
        })
        with self.assertRaisesRegex(ValueError, "counts do not match"):
            build_audit_report(observations, pd.DataFrame({"storm_id": ["a"]}), pd.DataFrame({"storm_id": ["a"]}), sample_manifest())

    def test_required_observation_fields_are_checked(self):
        observations = pd.DataFrame({"storm_id": ["a"], "time": ["2024-01-01T00:00:00Z"]})
        with self.assertRaisesRegex(ValueError, "missing required column"):
            build_audit_report(observations, pd.DataFrame({"storm_id": ["a"]}), pd.DataFrame({"storm_id": ["a"]}), sample_manifest())

    def test_source_manifest_requires_official_imd_host_and_valid_sha(self):
        manifest = sample_manifest()
        manifest["source_url"] = "https://example.org/fake.xlsx"
        with self.assertRaisesRegex(ValueError, "allowlisted official IMD/RSMC host"):
            validate_source_manifest(manifest)


if __name__ == "__main__":
    unittest.main()
