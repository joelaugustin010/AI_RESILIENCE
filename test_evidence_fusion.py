"""Tests for multi-source evidence gating; no test fixture represents real flood evidence."""
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from src import evidence_fusion


class MultiSourceEvidenceTests(unittest.TestCase):
    def test_empty_evidence_fails_closed_without_score(self):
        result = evidence_fusion.audit_multisource_evidence(
            [], now=datetime(2026, 10, 29, 12, tzinfo=timezone.utc)
        )
        self.assertEqual(result["status"], "INSUFFICIENT_EVIDENCE")
        self.assertFalse(result["numeric_prediction_allowed"])
        self.assertIsNone(result["risk_score"])
        self.assertTrue(result["blockers"])

    def test_unapproved_real_source_cannot_enter_numerical_fusion(self):
        result = evidence_fusion.audit_multisource_evidence(
            [{
                "source_id": "ksdma_historical_raster",
                "value": 12.0,
                "unit": "mm",
                "timestamp_utc": "2026-10-29T11:00:00Z",
                "quality_status": "verified",
                "location_match": "verified",
            }],
            now=datetime(2026, 10, 29, 12, tzinfo=timezone.utc),
        )
        self.assertEqual(result["accepted_count"], 0)
        self.assertIn("not approved", result["rejected_evidence"][0]["reason"].lower())
        self.assertIsNone(result["risk_score"])

    def test_multiple_independent_verified_families_are_review_only_not_prediction(self):
        registry = {
            "rain_test": {"family": "rain_gauge_observations", "title": "test rain",
                          "status": "verified_for_observation_use", "unit": "mm", "url": "https://example.org"},
            "river_test": {"family": "river_gauge_observations", "title": "test river",
                           "status": "verified_for_observation_use", "unit": "m", "url": "https://example.org"},
            "terrain_test": {"family": "terrain_and_drainage", "title": "test terrain",
                             "status": "verified_for_observation_use", "unit": "m", "url": "https://example.org"},
        }
        evidence = [
            {"source_id": "rain_test", "value": 12, "unit": "mm", "timestamp_utc": "2026-10-29T11:00:00Z",
             "quality_status": "verified", "location_match": "verified"},
            {"source_id": "river_test", "value": 2.4, "unit": "m", "timestamp_utc": "2026-10-29T11:05:00+00:00",
             "quality_status": "verified", "location_match": "verified"},
            {"source_id": "terrain_test", "value": 10, "unit": "m", "timestamp_utc": "2026-10-29T10:00:00Z",
             "quality_status": "verified", "location_match": "verified"},
        ]
        with patch.dict(evidence_fusion.SOURCE_REGISTRY, registry, clear=True):
            result = evidence_fusion.audit_multisource_evidence(
                evidence, now=datetime(2026, 10, 29, 12, tzinfo=timezone.utc)
            )
        self.assertEqual(result["status"], "MULTI_SOURCE_REVIEW_ONLY")
        self.assertEqual(result["accepted_count"], 3)
        self.assertFalse(result["numeric_prediction_allowed"])
        self.assertIsNone(result["risk_score"])

    def test_same_family_does_not_count_as_independent_corroboration(self):
        registry = {
            "rain_a": {"family": "rain_gauge_observations", "title": "rain A",
                       "status": "verified_for_observation_use", "unit": "mm", "url": "https://example.org"},
            "rain_b": {"family": "rain_gauge_observations", "title": "rain B",
                       "status": "verified_for_observation_use", "unit": "mm", "url": "https://example.org"},
        }
        evidence = [
            {"source_id": source_id, "value": 12, "unit": "mm", "timestamp_utc": "2026-10-29T11:00:00Z",
             "quality_status": "verified", "location_match": "verified"}
            for source_id in ("rain_a", "rain_b")
        ]
        with patch.dict(evidence_fusion.SOURCE_REGISTRY, registry, clear=True):
            result = evidence_fusion.audit_multisource_evidence(
                evidence, now=datetime(2026, 10, 29, 12, tzinfo=timezone.utc)
            )
        self.assertEqual(result["accepted_count"], 1)
        self.assertEqual(result["independent_source_families"], ["rain_gauge_observations"])
        self.assertTrue(result["blockers"])

    def test_stale_future_naive_and_unit_mismatch_are_rejected(self):
        registry = {
            "verified_rain": {"family": "rain_gauge_observations", "title": "rain",
                              "status": "verified_for_observation_use", "unit": "mm", "url": "https://example.org"},
        }
        base = {"source_id": "verified_rain", "value": 4, "unit": "mm",
                "quality_status": "verified", "location_match": "verified"}
        evidence = [
            {**base, "timestamp_utc": "2026-10-28T00:00:00Z"},
            {**base, "timestamp_utc": "2026-10-29T13:00:00Z"},
            {**base, "timestamp_utc": "2026-10-29T11:00:00"},
            {**base, "unit": "cm", "timestamp_utc": "2026-10-29T11:00:00Z"},
        ]
        with patch.dict(evidence_fusion.SOURCE_REGISTRY, registry, clear=True):
            result = evidence_fusion.audit_multisource_evidence(
                evidence, now=datetime(2026, 10, 29, 12, tzinfo=timezone.utc), max_age_hours=24
            )
        self.assertEqual(result["accepted_count"], 0)
        self.assertEqual(len(result["rejected_evidence"]), 4)


if __name__ == "__main__":
    unittest.main()
