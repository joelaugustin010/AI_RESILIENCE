from src import ernakulam_input_predictions as predictions


def test_prediction_options_require_a_validated_artifact(monkeypatch):
    monkeypatch.setattr(predictions, "load_hazard_model", lambda hazard_id: None)
    ready = predictions.prediction_ready_hazards("Ernakulam district (all areas)")
    assert ready == {}


def test_unavailable_hazards_explain_the_missing_evidence(monkeypatch):
    monkeypatch.setattr(predictions, "load_hazard_model", lambda hazard_id: None)
    reasons = predictions.prediction_unavailable_reasons("Ernakulam district (all areas)")
    assert set(reasons) == {spec["label"] for spec in predictions.HAZARD_MODELS.values()}
    assert all("No validated" in reason for reason in reasons.values())
