import math

import pytest

from src.mitigation_intelligence import (
    COMPONENT_CATALOG,
    build_design_state,
    design_recommendations,
    rainfall_category,
    review_project_register,
)


@pytest.mark.parametrize(
    ("rainfall", "expected"),
    [
        (0, "Low"),
        (29.9, "Low"),
        (30, "Moderate"),
        (69.9, "Moderate"),
        (70, "High"),
        (109.9, "High"),
        (110, "Very high"),
        (150, "Very high"),
    ],
)
def test_rainfall_category_boundaries(rainfall, expected):
    assert rainfall_category(rainfall) == expected


@pytest.mark.parametrize("rainfall", [-1, 150.1, math.nan, math.inf, -math.inf])
def test_design_state_rejects_invalid_rainfall(rainfall):
    with pytest.raises(ValueError):
        build_design_state(
            project_name="Test",
            area_type="Urban road",
            rainfall_mm_per_hour=rainfall,
            available_budget_inr=100000,
            selected_components={},
        )


@pytest.mark.parametrize("budget", [-1, math.nan, math.inf, -math.inf])
def test_design_state_rejects_invalid_budget(budget):
    with pytest.raises(ValueError):
        build_design_state(
            project_name="Test",
            area_type="Urban road",
            rainfall_mm_per_hour=50,
            available_budget_inr=budget,
            selected_components={},
        )


def test_design_state_uses_shared_component_catalogue():
    selected = {key: True for key in COMPONENT_CATALOG}
    state = build_design_state(
        project_name="Kochi pilot",
        area_type="Low-lying flood-prone area",
        rainfall_mm_per_hour=70,
        available_budget_inr=400000,
        selected_components=selected,
    )

    expected_total = sum(
        item["indicative_cost_inr"] for item in COMPONENT_CATALOG.values()
    )
    assert state["illustrative_component_cost_inr"] == expected_total
    assert state["budget_balance_inr"] == 400000 - expected_total
    assert state["budget_status"] == "Over budget"
    assert state["location"] == "Kochi, Kerala, India"


def test_recommendations_explain_their_trigger_and_verification():
    state = build_design_state(
        project_name="Low-lying pilot",
        area_type="Low-lying flood-prone area",
        rainfall_mm_per_hour=90,
        available_budget_inr=100000,
        selected_components={"drains": False, "garden": False},
    )

    recommendations = design_recommendations(state)
    titles = [item["Planning recommendation"] for item in recommendations]

    assert "Review drainage inspection and capacity" in titles
    assert "Review green-infrastructure opportunities" in titles
    assert all(item["Why this was suggested"] for item in recommendations)
    assert all(item["Suggested verification"] for item in recommendations)


def test_project_register_counts_unknown_cost_and_missing_evidence():
    rows = [
        {
            "Intervention": "Drain upgrade",
            "Location": "Kochi",
            "Cost INR": 125000,
            "Source / estimate date": "Estimate, Nov 2026",
            "Scope and unit": "100 metres",
            "Evidence for risk reduction": "Assessment report reference",
        },
        {
            "Intervention": "Pump station",
            "Location": "",
            "Cost INR": None,
            "Source / estimate date": "",
            "Scope and unit": "",
            "Evidence for risk reduction": "",
        },
    ]

    result = review_project_register(rows, 200000)

    assert result["project_count"] == 2
    assert result["known_cost_total_inr"] == 125000
    assert result["unknown_cost_count"] == 1
    assert result["within_budget"] is None
    assert result["review_rows"][0]["Review status"] == "Fields completed — verify evidence"
    assert result["review_rows"][1]["Review status"] == "Needs review"


def test_project_register_budget_arithmetic_when_all_costs_are_valid():
    rows = [
        {"Intervention": "A", "Cost INR": 100000},
        {"Intervention": "B", "Cost INR": 50000},
    ]

    result = review_project_register(rows, 200000)

    assert result["known_cost_total_inr"] == 150000
    assert result["remaining_budget_inr"] == 50000
    assert result["within_budget"] is True


def test_project_register_rejects_non_finite_costs():
    rows = [{"Intervention": "Invalid", "Cost INR": math.inf}]
    result = review_project_register(rows, 200000)

    assert result["unknown_cost_count"] == 1
    assert result["within_budget"] is None


def test_empty_project_register_is_safe():
    result = review_project_register([], 100000)

    assert result["project_count"] == 0
    assert result["known_cost_total_inr"] == 0
    assert result["unknown_cost_count"] == 0
    assert result["within_budget"] is True
