import pandas as pd
import pytest
from src.mitigation_priority_ml import PriorityModelDataError, prepare_priority_records, train_priority_model, predict_priority

def sample_records(n=90):
    rows = []
    for i in range(n):
        risk = (i % 5) + 1
        urgency = ((i * 2) % 5) + 1
        evidence = ((i * 3) % 5) + 1
        readiness = ((i * 4) % 5) + 1
        score = risk + urgency + evidence + readiness
        label = "Higher assessed priority" if score >= 15 else ("Moderate" if score >= 10 else "Further review")
        rows.append({
            "site_risk_severity": risk, "urgency": urgency,
            "evidence_strength": evidence, "implementation_readiness": readiness,
            "historical_priority_label": label, "source_reference": f"Verified project record {i+1}"
        })
    return pd.DataFrame(rows)

def test_requires_minimum_sourced_labelled_records():
    with pytest.raises(PriorityModelDataError, match="At least 40"):
        prepare_priority_records(sample_records(30))

def test_rejects_missing_sources_and_invalid_labels():
    data = sample_records()
    data.loc[0, "source_reference"] = ""
    data.loc[1, "historical_priority_label"] = "unknown"
    assert len(prepare_priority_records(data)) == 88

def test_train_returns_holdout_metrics_and_prediction():
    model = train_priority_model(sample_records())
    assert model["metrics"]["validation_records"] >= 8
    assert model["metrics"]["records_used"] == 90
    if model["metrics"]["beats_baseline"]:
        result = predict_priority(model, {
            "site_risk_severity": 5, "urgency": 5,
            "evidence_strength": 4, "implementation_readiness": 4
        })
        assert result["predicted_priority"] in ("Higher assessed priority", "Moderate", "Further review")
        assert 0 <= result["confidence"] <= 1

def test_prediction_rejects_invalid_assessment():
    model = train_priority_model(sample_records())
    if model["metrics"]["beats_baseline"]:
        with pytest.raises(PriorityModelDataError):
            predict_priority(model, {
                "site_risk_severity": 6, "urgency": 5,
                "evidence_strength": 4, "implementation_readiness": 4
            })
