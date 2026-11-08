import pytest

from src.mitigation_investment import score_investment_priority


def test_priority_score_uses_documented_weighted_inputs():
    result = score_investment_priority({
        "site_risk_severity": 5,
        "urgency": 5,
        "evidence_strength": 5,
        "implementation_readiness": 5,
    })
    assert result["score"] == 100
    assert result["band"] == "Higher assessed priority"


def test_priority_score_weights_risk_and_urgency_more_than_other_factors():
    result = score_investment_priority({
        "site_risk_severity": 5,
        "urgency": 5,
        "evidence_strength": 1,
        "implementation_readiness": 1,
    })
    assert result["score"] == 60


def test_priority_score_does_not_invent_missing_assessments():
    result = score_investment_priority({"site_risk_severity": 5})
    assert result["score"] is None
    assert len(result["missing"]) == 3
    assert result["band"] == "Not scored"


@pytest.mark.parametrize("value", [0, 6, 2.5, "unknown", None, float("nan")])
def test_priority_score_rejects_invalid_scale_values(value):
    result = score_investment_priority({
        "site_risk_severity": value,
        "urgency": 3,
        "evidence_strength": 3,
        "implementation_readiness": 3,
    })
    assert result["score"] is None
    assert "Site risk severity (1–5)" in result["missing"]
