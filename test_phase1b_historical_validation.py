"""Tests for fail-closed historical event validation readiness and metrics."""

import unittest

from src.historical_validation import (
    evaluate_binary_event_predictions,
    historical_validation_checklist,
    historical_validation_readiness,
)


def valid_case(**changes):
    case = {
        "event_id": "event-2020-001",
        "outcome_source_url": "https://example.org/independent-outcome",
        "outcome_definition": "Officially documented inundation at the named ward",
        "outcome_independent": True,
        "outcome_start": "2020-08-01T10:00:00+05:30",
        "outcome_end": "2020-08-01T16:00:00+05:30",
        "observation_source_url": "https://example.org/observations",
        "observation_time_basis": "Asia/Kolkata, offset +05:30",
        "feature_cutoff": "2020-08-01T09:00:00+05:30",
        "prediction_horizon_hours": 24,
        "geographic_match_method": "Reviewed polygon intersection with published CRS",
        "geographic_match_review": True,
        "temporal_match_method": "Observation cutoff before outcome start",
        "temporal_match_review": True,
        "dataset_sha256": "a" * 64,
        "code_version": "abc123",
        "model_version": "baseline-v1",
        "split_assignment": "held-out-event-test",
    }
    case.update(changes)
    return case


class HistoricalValidationReadinessTests(unittest.TestCase):
    def test_complete_case_passes_readiness_but_not_scientific_validation(self):
        result = historical_validation_readiness(valid_case())
        self.assertTrue(result["ready"])
        self.assertIn("Not established", result["scientific_validity"])

    def test_missing_independent_outcome_and_provenance_block_readiness(self):
        result = historical_validation_readiness(
            valid_case(outcome_independent=False, dataset_sha256="bad", code_version="")
        )
        self.assertFalse(result["ready"])
        joined = " ".join(result["blockers"])
        self.assertIn("independently reviewed", joined)
        self.assertIn("64 hexadecimal", joined)
        self.assertIn("code revision", joined.lower())

    def test_feature_cutoff_at_or_after_outcome_is_temporal_leakage(self):
        result = historical_validation_readiness(
            valid_case(feature_cutoff="2020-08-01T10:00:00+05:30")
        )
        self.assertTrue(any("temporal leakage" in blocker for blocker in result["blockers"]))

    def test_incomparable_timezones_and_reversed_period_are_blocked(self):
        result = historical_validation_readiness(
            valid_case(
                outcome_start="2020-08-01T10:00:00",
                outcome_end="2020-08-01T09:00:00",
                feature_cutoff="2020-08-01T08:00:00+05:30",
            )
        )
        joined = " ".join(result["blockers"])
        self.assertIn("precedes", joined)
        self.assertIn("comparable timezone", joined)

    def test_checklist_covers_matching_leakage_error_audit_and_reproducibility(self):
        checklist = historical_validation_checklist()
        combined = " ".join(checklist["Validation stage"])
        self.assertIn("Geographic matching", combined)
        self.assertIn("Temporal matching", combined)
        self.assertIn("Leakage-safe evaluation", combined)
        self.assertIn("Metrics and errors", combined)
        self.assertIn("Reproducibility", combined)


class BinaryMetricTests(unittest.TestCase):
    def test_confusion_metrics_and_error_case_ids_are_reported(self):
        result = evaluate_binary_event_predictions(
            [1, 0, 1, 0],
            [1, 1, 0, 0],
            ["tp", "fp", "fn", "tn"],
        )
        self.assertEqual((result["true_positive"], result["false_positive"]), (1, 1))
        self.assertEqual((result["false_negative"], result["true_negative"]), (1, 1))
        self.assertEqual(result["false_positive_case_ids"], ["fp"])
        self.assertEqual(result["false_negative_case_ids"], ["fn"])
        self.assertEqual(result["recall_sensitivity"], 0.5)
        self.assertEqual(result["specificity"], 0.5)

    def test_undefined_metrics_remain_null_and_invalid_inputs_fail(self):
        result = evaluate_binary_event_predictions([0, 0], [0, 0], ["a", "b"])
        self.assertIsNone(result["precision"])
        self.assertIsNone(result["recall_sensitivity"])
        with self.assertRaises(ValueError):
            evaluate_binary_event_predictions([], [], [])
        with self.assertRaises(ValueError):
            evaluate_binary_event_predictions([1], [2], ["x"])


if __name__ == "__main__":
    unittest.main()
