"""End-to-end output contract for all ten selectable Decision Workflow hazards."""

from src.consequence_assessment import build_consequence_assessment
from src.consequence_data_requirements import requirements_for_hazard
from src.decision_workflow import HAZARD_OPTIONS, mitigation_actions_for
from src.hazard_registry import WORKFLOW_HAZARDS
from src.prevention_intelligence import generate_prevention_actions
from src.scenario_output_model import HAZARDS as SCENARIO_HAZARDS, predict_scenario_outcome


def test_all_ten_hazards_are_consistent_across_the_workflow_registry():
    assert len(WORKFLOW_HAZARDS) == 10
    assert tuple(HAZARD_OPTIONS) == WORKFLOW_HAZARDS
    assert tuple(SCENARIO_HAZARDS) == WORKFLOW_HAZARDS


def test_every_hazard_produces_the_complete_non_fabricated_output_contract():
    for hazard in WORKFLOW_HAZARDS:
        inputs = {
            "hazard": hazard,
            "location": "Kochi (user-specified scenario area)",
            "input_classification": "Hypothetical scenario assumption",
        }

        scenario = predict_scenario_outcome(inputs)
        consequences = build_consequence_assessment(
            hazard,
            inputs["location"],
            inputs["input_classification"],
            inputs,
        )
        requirements = requirements_for_hazard(hazard)
        preventive = generate_prevention_actions(hazard, inputs)
        mitigation = mitigation_actions_for(hazard)

        assert scenario["hazard"] == hazard
        assert scenario["conditional_outcome"].strip()
        assert scenario["concern_level"].strip()
        assert scenario["recommended_checks"]
        assert scenario["limitations"]
        assert scenario["numerical_probability"] is None
        assert scenario["is_trained_ml"] is False
        assert scenario["is_official_warning"] is False

        assert consequences["hazard"] == hazard
        assert consequences["consequence_categories"]
        assert consequences["required_evidence"]
        assert consequences["current_blockers"]
        assert consequences["prediction_permitted"] is False
        assert consequences["official_warning_permitted"] is False

        assert requirements["supported"] is True
        assert requirements["workflow_supported"] is True
        assert requirements["hazard_inputs"].strip()
        assert requirements["process_data"].strip()
        assert requirements["impact_labels"].strip()

        assert preventive
        assert any(row["hazard"] != "All selected hazards" for row in preventive)
        assert all(row["action"] and row["trigger"] and row["owner"] and row["caution"] for row in preventive)
        assert not mitigation.empty
        assert mitigation["Action"].astype(str).str.strip().ne("").all()


def test_compound_hazards_keep_joint_assessment_and_component_actions():
    cases = {
        "Compound: cyclone + flood": {"Cyclone", "Flood"},
        "Compound: heavy rainfall + drainage failure": {"Flood", "Infrastructure failure"},
    }
    for hazard, expected_components in cases.items():
        actions = generate_prevention_actions(hazard)
        action_hazards = {row["hazard"] for row in actions}
        assert expected_components.issubset(action_hazards)
        assert any(row["hazard"] == hazard for row in actions)


def test_invalid_numeric_inputs_block_scenario_assessment_for_all_ten_hazards():
    from src.scenario_output_model import validate_scenario_inputs
    for hazard in WORKFLOW_HAZARDS:
        result = predict_scenario_outcome({"hazard": hazard, "rainfall_mm": "not-a-number"})
        assert result["concern_level"] == "Input validation required"
        assert "not assessed" in result["conditional_outcome"].lower()
        assert result["numerical_probability"] is None
        assert result["is_trained_ml"] is False
        assert result["input_validation"]["valid"] is False
        assert result["input_validation"]["problems"][0]["field"] == "rainfall_mm"


def test_numeric_input_validation_rejects_nonfinite_out_of_range_and_fractional_counts():
    from src.scenario_output_model import validate_scenario_inputs
    cases = [
        ({"wind_speed_kmh": float("nan")}, "wind_speed_kmh"),
        ({"temperature_c": 120}, "temperature_c"),
        ({"earthquake_magnitude": -1}, "earthquake_magnitude"),
        ({"heatwave_consecutive_days": 2.5}, "heatwave_consecutive_days"),
        ({"river_level_m": True}, "river_level_m"),
    ]
    for values, expected_field in cases:
        problems = validate_scenario_inputs(values)
        assert problems and problems[0]["field"] == expected_field


def test_valid_numeric_strings_are_accepted_as_measurements():
    from src.scenario_output_model import validate_scenario_inputs
    assert validate_scenario_inputs({"rainfall_mm": "120.5", "wind_speed_kmh": "45"}) == []