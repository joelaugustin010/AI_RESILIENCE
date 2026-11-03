from src.hazard_screening import HAZARD_CONFIG, LEVELS, assess_all_hazards, assess_hazard

def test_all_four_hazards_are_assessed():
    inputs = {
        hazard: {key: "Some concern" for key, _, _ in config["indicators"]}
        for hazard, config in HAZARD_CONFIG.items()
    }
    results = assess_all_hazards(inputs)
    assert list(results) == list(HAZARD_CONFIG)
    assert all(result["category"] == "Some concern reported" for result in results.values())

def test_unknown_inputs_are_not_treated_as_zero():
    result = assess_hazard({"rainfall": "Not known / not checked", "river": "No elevated condition reported"})
    assert result["assessed_count"] == 1
    assert result["unknown_count"] == 1
    assert result["category"] == "No elevated indicators reported"

def test_all_unknown_is_insufficient_information():
    result = assess_hazard({"rainfall": "Not known / not checked"})
    assert result["category"] == "Insufficient information"
    assert result["probability"] is None
    assert result["risk_score"] is None

def test_strong_concern_is_flagged_without_probability():
    result = assess_hazard({"wind": "Strong concern", "storm": "Not known / not checked"})
    assert result["category"] == "Elevated concern reported"
    assert result["probability"] is None
    assert result["risk_score"] is None

def test_missing_hazard_is_rejected():
    try:
        assess_all_hazards({})
    except ValueError as exc:
        assert "Missing hazard inputs" in str(exc)
    else:
        raise AssertionError("Expected missing hazard inputs to fail")

def test_unknown_level_is_rejected():
    try:
        assess_hazard({"rainfall": "Extreme"})
    except ValueError:
        pass
    else:
        raise AssertionError("Expected invalid level to fail")
