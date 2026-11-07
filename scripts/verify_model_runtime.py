"""Load every registered model artifact and verify its inference interface.

This proves that the committed binaries can be deserialized in the CI Python
environment and match their model-card feature contract. It does not score
predictions, establish scientific validity, or prove the live Streamlit process
loaded the same release.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import joblib

from scripts.verify_release_artifacts import EXPECTED_MODEL_IDS


def inspect_loaded_model(model_id: str, card: dict[str, Any], pipeline: Any) -> dict[str, Any]:
    features = card.get("feature_columns")
    if not isinstance(features, list) or not features or any(not isinstance(x, str) for x in features):
        raise ValueError(f"{model_id}: invalid feature_columns contract")
    if card.get("model_id") != model_id:
        raise ValueError(f"{model_id}: model-card ID mismatch")
    declared_count = card.get("feature_count")
    if declared_count is not None and int(declared_count) != len(features):
        raise ValueError(f"{model_id}: feature_count does not match feature_columns")
    loaded_count = getattr(pipeline, "n_features_in_", None)
    if loaded_count is not None and int(loaded_count) != len(features):
        raise ValueError(
            f"{model_id}: loaded estimator expects {loaded_count} features; card declares {len(features)}"
        )
    task = card.get("task_type", "classification")
    if task == "regression":
        if not callable(getattr(pipeline, "predict", None)):
            raise ValueError(f"{model_id}: regression artifact has no predict method")
    else:
        if not callable(getattr(pipeline, "predict_proba", None)):
            raise ValueError(f"{model_id}: classification artifact has no predict_proba method")
        estimator = pipeline.steps[-1][1] if getattr(pipeline, "steps", None) else pipeline
        classes = list(getattr(estimator, "classes_", []))
        if 1 not in classes:
            raise ValueError(f"{model_id}: classifier artifact has no positive class 1")
    return {
        "model_id": model_id,
        "task_type": task,
        "feature_count": len(features),
        "artifact_load": "passed",
        "interface_check": "passed",
    }


def verify_runtime_models(root: Path) -> dict[str, Any]:
    results = []
    problems = []
    for model_id in sorted(EXPECTED_MODEL_IDS):
        directory = root / "models" / "ml" / model_id
        artifact = directory / "model.joblib"
        card_path = directory / "model_card.json"
        try:
            card = json.loads(card_path.read_text(encoding="utf-8"))
            pipeline = joblib.load(artifact)
            result = inspect_loaded_model(model_id, card, pipeline)
            result["artifact_sha256"] = hashlib.sha256(artifact.read_bytes()).hexdigest()
            results.append(result)
        except Exception as exc:
            problems.append(f"{model_id}: {type(exc).__name__}: {exc}")
    return {
        "passed": not problems and len(results) == len(EXPECTED_MODEL_IDS),
        "expected_models": len(EXPECTED_MODEL_IDS),
        "loaded_models": len(results),
        "models": results,
        "problems": problems,
        "scope": (
            "CI checkout deserialization and feature-interface verification only; "
            "not live-process verification, empirical validation, or operational clearance."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, default=Path("reports/model_runtime_load_check.json"))
    args = parser.parse_args()
    report = verify_runtime_models(args.root.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
