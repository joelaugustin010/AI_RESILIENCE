"""Tests for the evidence-gated validation utilities."""
import math
import unittest

import numpy as np

from src.ml.validation_gates import (
    binary_calibration_report,
    model_card_validation_gate,
    registry_validation_summary,
    split_conformal_interval,
)


class BinaryCalibrationReportTests(unittest.TestCase):
    def test_reports_brier_base_rate_and_reliability_bins(self):
        result = binary_calibration_report([0, 0, 1, 1], [0.1, 0.2, 0.8, 0.9], n_bins=5)
        self.assertAlmostEqual(result["brier_score"], 0.025)
        self.assertAlmostEqual(result["base_rate_brier_score"], 0.25)
        self.assertGreater(result["brier_skill_over_base_rate"], 0)
        self.assertEqual(sum(row["n"] for row in result["reliability_bins"]), 4)

    def test_rejects_invalid_probability(self):
        with self.assertRaises(ValueError):
            binary_calibration_report([0, 1], [0.2, 1.2])

    def test_rejects_non_binary_labels(self):
        with self.assertRaises(ValueError):
            binary_calibration_report([0, 2], [0.2, 0.8])


class SplitConformalTests(unittest.TestCase):
    def test_builds_finite_interval_when_calibration_sample_is_large_enough(self):
        result = split_conformal_interval(
            [1, 2, 3, 4, 5], [1, 2, 3, 4, 5], [10, 20], alpha=0.2
        )
        self.assertTrue(result["finite_interval"])
        self.assertEqual(result["lower"], [10.0, 20.0])
        self.assertEqual(result["upper"], [10.0, 20.0])

    def test_small_calibration_sample_returns_infinite_interval_when_required(self):
        result = split_conformal_interval([1], [0], [4], alpha=0.1)
        self.assertFalse(result["finite_interval"])
        self.assertTrue(math.isinf(result["absolute_residual_quantile"]))

    def test_rejects_invalid_alpha(self):
        with self.assertRaises(ValueError):
            split_conformal_interval([1, 2], [1, 2], [3], alpha=1.0)


class ModelCardGateTests(unittest.TestCase):
    def test_single_holdout_weak_signal_is_never_operational(self):
        result = model_card_validation_gate({
            "model_id": "rainfall",
            "status": "WEAK_RESEARCH_SIGNAL",
            "validation_status": "SINGLE_TEMPORAL_HOLDOUT_NOT_INDEPENDENTLY_VALIDATED",
            "metrics": {"brier_score": 0.08},
        })
        self.assertFalse(result["operational_eligible"])
        self.assertEqual(result["readiness"], "RESEARCH_ONLY")
        self.assertGreaterEqual(len(result["blocking_reasons"]), 7)

    def test_operational_gate_requires_all_independent_evidence(self):
        card = {
            "model_id": "candidate",
            "status": "VALIDATED",
            "validation_status": "INDEPENDENT_VALIDATION_PASSED",
            "metrics": {"mae": 1.0},
            "independent_validation": {
                "temporal_holdouts_passed": True,
                "spatial_holdouts_passed": True,
                "calibration_passed": True,
                "baseline_skill_passed": True,
                "provenance_complete": True,
                "domain_transfer_passed": True,
                "independent_test_events": 120,
            },
        }
        self.assertTrue(model_card_validation_gate(card)["operational_eligible"])

    def test_regression_gate_uses_independent_cases_not_positive_event_count(self):
        card = {
            "model_id": "temperature-regression",
            "task_type": "regression",
            "status": "VALIDATED",
            "validation_status": "INDEPENDENT_VALIDATION_PASSED",
            "metrics": {"mae": 0.5},
            "independent_validation": {
                "temporal_holdouts_passed": True,
                "spatial_holdouts_passed": True,
                "calibration_passed": True,
                "baseline_skill_passed": True,
                "provenance_complete": True,
                "domain_transfer_passed": True,
                "independent_test_cases": 150,
            },
        }
        self.assertTrue(model_card_validation_gate(card)["operational_eligible"])

    def test_registry_summary_does_not_infer_validity_from_artifact_count(self):
        result = registry_validation_summary([
            {"model_id": "a", "status": "WEAK_RESEARCH_SIGNAL"}
        ])
        self.assertEqual(result["model_count"], 1)
        self.assertEqual(result["operational_eligible_count"], 0)


if __name__ == "__main__":
    unittest.main()
