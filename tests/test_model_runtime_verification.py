from types import SimpleNamespace

import pytest

from scripts.verify_model_runtime import inspect_loaded_model


def test_classifier_artifact_interface_matches_card():
    pipeline = SimpleNamespace(
        n_features_in_=2,
        steps=[("classifier", SimpleNamespace(classes_=[0, 1]))],
        predict_proba=lambda x: None,
    )
    card = {"model_id":"m", "feature_columns":["rain","temperature"], "feature_count":2}
    result = inspect_loaded_model("m", card, pipeline)
    assert result["artifact_load"] == "passed"
    assert result["task_type"] == "classification"


def test_regression_artifact_requires_predict_interface():
    pipeline = SimpleNamespace(n_features_in_=1, predict=lambda x: None)
    card = {"model_id":"m", "task_type":"regression", "feature_columns":["rain"]}
    assert inspect_loaded_model("m", card, pipeline)["interface_check"] == "passed"


def test_feature_count_mismatch_is_rejected():
    pipeline = SimpleNamespace(n_features_in_=3, predict=lambda x: None)
    card = {"model_id":"m", "task_type":"regression", "feature_columns":["rain","temperature"]}
    with pytest.raises(ValueError, match="expects 3 features"):
        inspect_loaded_model("m", card, pipeline)
