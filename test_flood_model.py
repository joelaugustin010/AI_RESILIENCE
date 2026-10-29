"""Readiness and pipeline tests; synthetic rows here test plumbing only."""

import unittest
import hashlib
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

from src.flood_model import (
    FEATURE_COLUMNS,
    TARGET,
    audit_flood_dataset,
    evaluate_flood_model,
    load_flood_data,
    predict_flood_probability,
)


def synthetic_fixture() -> tuple[pd.DataFrame, dict]:
    """Build controlled synthetic records isolated to this test module."""
    rows = []
    dates = pd.date_range("2025-01-01", periods=12, freq="D")
    for day_index, timestamp in enumerate(dates):
        for within_day in range(20):
            row_index = day_index * 20 + within_day
            label = within_day % 2
            rows.append({
                "observation_date": timestamp.isoformat(),
                "event_group_id": f"synthetic-event-{row_index:03d}",
                "antecedent_rainfall_3day_mm": 15 + 100 * label + within_day / 10,
                "forecast_rainfall_24h_mm": 10 + 80 * label + within_day / 10,
                "insat3d_ipwv_mm": 25 + 20 * label,
                "soil_moisture_percent": 30 + 60 * label,
                "slope_angle_deg": 3 + label,
                "river_gauge_height_m": 1 + 5 * label,
                "danger_level_m": 3 + label,
                "cwc_flood_warning_level": "High" if label else "Normal",
                TARGET: label,
            })
    metadata = {
        "data_kind": "synthetic_test_fixture",
        "event_group_column": "event_group_id",
        "feature_availability_cutoff": "Synthetic predictors generated before the fixture outcome for pipeline tests.",
    }
    return pd.DataFrame(rows), metadata


def unverified_demo_fixture() -> tuple[pd.DataFrame, dict]:
    """Build a tiny, explicitly unverified sample without reading repository data."""
    frame, _ = synthetic_fixture()
    frame = frame.iloc[:5].copy()
    frame[TARGET] = [1, 1, 1, 0, 0]
    frame["observation_date"] = "2026-10-19T12:00:00"
    frame = frame.drop(columns=["event_group_id"])
    return frame, {"data_kind": "unverified_demo"}


class FloodModelReadinessTests(unittest.TestCase):
    def test_five_unverified_rows_are_blocked_with_auditable_reasons(self):
        frame, metadata = unverified_demo_fixture()
        report = audit_flood_dataset(frame, metadata)
        self.assertFalse(report["ready"])
        self.assertEqual(report["rows"], 5)
        self.assertEqual(report["target_counts"], {"1": 3, "0": 2})
        self.assertEqual(report["distinct_dates"], 1)
        self.assertEqual(report["exact_duplicates"], 0)
        self.assertTrue(any("verified real observations" in item for item in report["blockers"]))
        self.assertTrue(any("chronological" in item for item in report["blockers"]))
        self.assertTrue(any("event-group column" in item for item in report["blockers"]))

    def test_missing_columns_and_invalid_labels_are_blocked(self):
        frame, metadata = synthetic_fixture()
        report = audit_flood_dataset(frame.drop(columns=[FEATURE_COLUMNS[0]]), metadata, allow_synthetic_test_fixture=True)
        self.assertTrue(any("Missing required columns" in item for item in report["blockers"]))
        bad_labels = frame.copy()
        bad_labels.loc[0, TARGET] = 2
        report = audit_flood_dataset(bad_labels, metadata, allow_synthetic_test_fixture=True)
        self.assertTrue(any("binary labels" in item for item in report["blockers"]))

    def test_synthetic_data_is_blocked_outside_explicit_test_mode(self):
        frame, metadata = synthetic_fixture()
        report = audit_flood_dataset(frame, metadata)
        self.assertFalse(report["ready"])
        self.assertTrue(any("test fixtures" in item for item in report["blockers"]))

    def test_insufficient_class_and_invalid_input_data_are_blocked(self):
        frame, metadata = synthetic_fixture()
        small = frame.iloc[:20].copy()
        report = audit_flood_dataset(small, metadata, allow_synthetic_test_fixture=True)
        self.assertTrue(any("Only 20 rows" in item for item in report["blockers"]))
        invalid = frame.copy()
        invalid.loc[0, "soil_moisture_percent"] = 150
        invalid.loc[1, "observation_date"] = "not-a-date"
        report = audit_flood_dataset(invalid, metadata, allow_synthetic_test_fixture=True)
        self.assertTrue(any("outside its documented basic range" in item for item in report["blockers"]))
        self.assertTrue(any("timestamp(s) are invalid" in item for item in report["blockers"]))

    def test_synthetic_fixture_trains_against_prior_baseline_and_keeps_events_separate(self):
        frame, metadata = synthetic_fixture()
        result = evaluate_flood_model(frame, metadata, allow_synthetic_test_fixture=True)
        self.assertEqual(result["model_metrics"]["test_rows"], 60)
        self.assertEqual(result["baseline_metrics"]["test_rows"], 60)
        self.assertEqual(len(result["model_metrics"]["confusion_matrix_labels_0_1"][0]), 2)
        self.assertEqual(result["split"]["event_groups_overlap"], [])
        self.assertEqual(result["readiness"]["warnings"][0].split(":")[0], "Synthetic fixture mode")

    def test_inference_returns_bounded_positive_class_score_and_rejects_bad_inputs(self):
        frame, metadata = synthetic_fixture()
        model = evaluate_flood_model(frame, metadata, allow_synthetic_test_fixture=True)["model"]
        sample = frame.iloc[0][list(FEATURE_COLUMNS)].to_dict()
        score = predict_flood_probability(model, sample)
        self.assertTrue(0.0 <= score <= 1.0)
        with self.assertRaisesRegex(ValueError, "Missing required prediction inputs"):
            predict_flood_probability(model, {"cwc_flood_warning_level": "Normal"})
        sample["soil_moisture_percent"] = np.inf
        with self.assertRaisesRegex(ValueError, "must be finite"):
            predict_flood_probability(model, sample)
        sample = frame.iloc[0][list(FEATURE_COLUMNS)].to_dict()
        sample["soil_moisture_percent"] = 101
        with self.assertRaisesRegex(ValueError, "between 0 and 100"):
            predict_flood_probability(model, sample)

    def test_loader_checks_a_synthetic_csv_and_provenance_hash(self):
        frame, metadata = unverified_demo_fixture()
        with tempfile.TemporaryDirectory() as folder:
            data_path = Path(folder) / "fixture.csv"
            metadata_path = Path(folder) / "fixture.metadata.json"
            csv_bytes = frame.to_csv(index=False).encode("utf-8")
            data_path.write_bytes(csv_bytes)
            metadata["raw_sha256"] = hashlib.sha256(csv_bytes).hexdigest()
            metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
            with patch("src.flood_model.DATA_PATH", data_path), patch(
                "src.flood_model.METADATA_PATH", metadata_path
            ):
                loaded, loaded_metadata = load_flood_data()
        self.assertEqual(len(loaded), 5)
        self.assertTrue(loaded_metadata["raw_hash_matches"])

    def test_real_observation_metadata_requires_independent_sources_and_feature_crosswalk(self):
        frame, metadata = synthetic_fixture()
        metadata.update({
            "data_kind": "verified_observations",
            "publisher": "Test publisher",
            "source_url": "https://example.org/dataset",
            "retrieved_on": "2026-10-29",
            "license": "Test-only terms",
            "geographic_coverage": "Test-only fixture",
            "label_definition": "Test-only binary label",
            "label_source": "Test fixture labels",
            "label_review_status": "independently_verified",
            "feature_availability_cutoff": "Test fixture predictors precede labels",
            "time_zone": "UTC",
            "prediction_horizon_hours": 24,
        })
        report = audit_flood_dataset(frame, metadata)
        self.assertFalse(report["ready"])
        self.assertTrue(any("Feature provenance must map every model feature" in item for item in report["blockers"]))
        self.assertTrue(any("Independent source families must be documented" in item for item in report["blockers"]))
        self.assertTrue(any("crosswalk" in item.lower() for item in report["blockers"]))

    def test_evaluation_refuses_the_unverified_demo_fixture(self):
        frame, metadata = unverified_demo_fixture()
        with self.assertRaisesRegex(ValueError, "evaluation blocked"):
            evaluate_flood_model(frame, metadata)


if __name__ == "__main__":
    unittest.main()
