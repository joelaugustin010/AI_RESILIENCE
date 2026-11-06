from __future__ import annotations

from src.hazard_registry import WORKFLOW_HAZARDS
from src.prevention_intelligence import generate_prevention_actions


def test_every_registered_hazard_has_preventive_actions():
    for hazard in WORKFLOW_HAZARDS:
        actions = generate_prevention_actions(hazard)
        assert actions
        assert any(item["hazard"] != "All selected hazards" for item in actions)
        assert all(item["action"] and item["trigger"] and item["caution"] for item in actions)


def test_compound_selection_includes_both_component_hazards():
    actions = generate_prevention_actions(["Flood", "Cyclone"])
    hazards = {item["hazard"] for item in actions}
    assert "Flood" in hazards
    assert "Cyclone" in hazards


def test_compound_cyclone_flood_adds_joint_timeline_and_route_review():
    actions = generate_prevention_actions("Compound: cyclone + flood")
    assert any(
        item["hazard"] == "Compound: cyclone + flood"
        and "incident timeline" in item["action"].lower()
        for item in actions
    )
    assert any(
        item["hazard"] == "Compound: cyclone + flood"
        and "route" in item["action"].lower()
        for item in actions
    )


def test_compound_rainfall_drainage_adds_asset_specific_operator_action():
    actions = generate_prevention_actions("Compound: heavy rainfall + drainage failure")
    assert any(
        item["hazard"] == "Compound: heavy rainfall + drainage failure"
        and "drainage operator" in item["owner"].lower()
        for item in actions
    )


def test_entered_rainfall_adds_provenance_check_not_warning_threshold():
    actions = generate_prevention_actions(
        "Flood",
        {"rainfall_mm": "120", "input_classification": "Hypothetical scenario assumption"},
    )
    item = next(row for row in actions if row["phase"] == "Verify evidence")
    assert "station" in item["action"].lower()
    assert "does not authenticate" in item["caution"].lower() or "does not authenticate" in item["caution"].lower()
    assert "threshold" not in item["trigger"].lower()


def test_reported_drainage_impairment_adds_operator_referral():
    actions = generate_prevention_actions(
        ["Flood", "Compound: heavy rainfall + drainage failure"],
        {"drainage_status": "Reported partially impaired"},
    )
    assert any(
        item["hazard"] == "Drainage failure"
        and "responsible operator" in item["action"].lower()
        for item in actions
    )


def test_nominated_critical_services_receive_continuity_actions():
    actions = generate_prevention_actions("Cyclone", {"services": ["Hospitals", "Electricity"]})
    nominated = [item for item in actions if item["hazard"] == "Critical-service continuity"]
    assert len(nominated) == 2
    assert all("backup" in item["action"].lower() for item in nominated)


def test_custom_disaster_gets_general_specialist_review_without_fake_specific_model():
    actions = generate_prevention_actions([], {}, custom_disaster="Unknown industrial event")
    item = next(row for row in actions if row["hazard"] == "Unregistered / custom scenario")
    assert "qualified specialist" in item["action"].lower()
    assert "no hazard-specific model" in item["caution"].lower()


def test_actions_are_not_ranked_or_assigned_risk_reduction_scores():
    actions = generate_prevention_actions("Compound: cyclone + flood")
    assert all("score" not in item for item in actions)
    assert all("risk_reduction_percent" not in item for item in actions)


def test_every_workflow_hazard_has_before_during_and_recovery_actions():
    for hazard in WORKFLOW_HAZARDS:
        actions = generate_prevention_actions(hazard)
        phases = {item["phase"] for item in actions}
        assert "Before the event" in phases, hazard
        assert any(
            phase in {"During the event", "When an official warning is issued",
                      "When an official alert is issued", "After shaking"}
            for phase in phases
        ), hazard
        assert any(phase.startswith("After") for phase in phases), hazard
