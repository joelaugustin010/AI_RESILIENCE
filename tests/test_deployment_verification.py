"""Unit tests for deployment and release verification scripts."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.verify_live_deployment import verify_deployment
from scripts.verify_release_artifacts import EXPECTED_MODEL_IDS, verify_release_bundle


class _Response:
    def __init__(self, status: int, body: str):
        self.status = status
        self._body = body.encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, _limit: int):
        return self._body


class DeploymentSmokeTests(unittest.TestCase):
    @patch("scripts.verify_live_deployment.urlopen")
    def test_health_and_streamlit_shell_must_both_pass(self, mocked):
        mocked.side_effect = [
            _Response(200, "ok"),
            _Response(200, "<html><script>window.streamlit</script></html>"),
        ]
        result = verify_deployment("https://example.streamlit.app")
        self.assertTrue(result["passed"])
        self.assertEqual(mocked.call_count, 2)

    @patch("scripts.verify_live_deployment.urlopen")
    def test_health_failure_does_not_pass(self, mocked):
        mocked.side_effect = [
            _Response(503, "unavailable"),
            _Response(200, "<html>streamlit</html>"),
        ]
        result = verify_deployment("https://example.streamlit.app")
        self.assertFalse(result["passed"])

    def test_rejects_non_https_url(self):
        with self.assertRaises(ValueError):
            verify_deployment("http://example.com")


class ReleaseArtifactTests(unittest.TestCase):
    def test_complete_research_bundle_is_integrity_checked_without_promotion(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for model_id in EXPECTED_MODEL_IDS:
                directory = root / "models" / "ml" / model_id
                directory.mkdir(parents=True)
                (directory / "model.joblib").write_bytes(b"artifact")
                (directory / "model_card.json").write_text(json.dumps({
                    "model_id": model_id,
                    "feature_columns": ["x"],
                    "validation_status": "SINGLE_TEMPORAL_HOLDOUT_NOT_INDEPENDENTLY_VALIDATED",
                }), encoding="utf-8")
            reports = root / "reports"
            reports.mkdir()
            (reports / "ml_model_registry.json").write_text("{}", encoding="utf-8")
            (reports / "ml_validation_report.json").write_text(
                json.dumps({"validated_models": 0}), encoding="utf-8"
            )
            (reports / "ml_disaster_coverage.json").write_text(json.dumps({
                "validated_models": 0,
                "n_hazards": 10,
                "predictive_model_coverage_complete": False,
            }), encoding="utf-8")
            result = verify_release_bundle(root)
            self.assertTrue(result["passed"], result["problems"])
            self.assertEqual(result["validated_models_reported"], 0)

    def test_missing_model_artifact_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            result = verify_release_bundle(Path(temp))
            self.assertFalse(result["passed"])
            self.assertTrue(result["problems"])


if __name__ == "__main__":
    unittest.main()
