"""Tests for observed local hazard panel readiness contracts."""
import unittest

from src.ml.local_panel_contracts import audit_observed_hazard_panel


def row(unit, label, status, *, origin="observed", source="record-1"):
    return {
        "hazard": "Flood",
        "unit_id": unit,
        "observation_start": "2024-06-01T00:00:00+00:00",
        "observation_end": "2024-06-02T00:00:00+00:00",
        "event_label": label,
        "observation_status": status,
        "label_source_id": source,
        "record_origin": origin,
        "latitude": 9.98,
        "longitude": 76.28,
    }


class LocalPanelContractTests(unittest.TestCase):
    def test_unknown_and_synthetic_rows_never_become_non_events(self):
        records = [
            row("ward-a", 0, "unknown", source="unverified"),
            row("ward-b", 0, "verified_non_event", origin="synthetic"),
        ]
        result = audit_observed_hazard_panel(
            records, hazard="Flood", minimum_events=1, minimum_non_events=1
        )
        self.assertFalse(result["training_ready"])
        self.assertEqual(result["verified_non_event_rows"], 0)
        self.assertEqual(result["excluded_rows"], 1)
        self.assertTrue(any("verified_non_event" in issue for issue in result["issues"]))

    def test_only_verified_observed_events_and_non_events_count(self):
        records = [
            row("ward-a", 1, "verified_event", source="flood-report-1"),
            row("ward-b", 0, "verified_non_event", source="survey-2"),
        ]
        result = audit_observed_hazard_panel(
            records, hazard="Flood", minimum_events=1, minimum_non_events=1
        )
        self.assertTrue(result["training_ready"])
        self.assertEqual(result["verified_event_rows"], 1)
        self.assertEqual(result["verified_non_event_rows"], 1)

    def test_duplicate_unit_time_interval_is_rejected(self):
        records = [
            row("ward-a", 1, "verified_event", source="flood-report-1"),
            row("ward-a", 1, "verified_event", source="flood-report-2"),
        ]
        result = audit_observed_hazard_panel(
            records, hazard="Flood", minimum_events=1, minimum_non_events=1
        )
        self.assertFalse(result["training_ready"])
        self.assertTrue(any("duplicate unit/time" in issue for issue in result["issues"]))

    def test_missing_label_provenance_is_rejected(self):
        record = row("ward-a", 1, "verified_event", source="")
        result = audit_observed_hazard_panel(
            [record], hazard="Flood", minimum_events=1, minimum_non_events=1
        )
        self.assertFalse(result["training_ready"])
        self.assertTrue(any("label_source_id" in issue for issue in result["issues"]))

    def test_wrong_hazard_is_rejected(self):
        with self.assertRaises(ValueError):
            audit_observed_hazard_panel([], hazard="Volcano")


if __name__ == "__main__":
    unittest.main()
