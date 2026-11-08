import math

import pytest

from src.smart_mitigation_studio import (
    build_review_items,
    calculate_design,
    compare_designs,
)


def test_calculate_design_uses_selected_quantities_and_rates():
    result = calculate_design(
        budget_inr=100000,
        selected={"drains": True, "garden": True},
        quantities={"drains": 2, "garden": 1},
        rates_inr={"drains": 30000, "garden": 20000},
    )
    assert result["component_count"] == 2
    assert result["total_inr"] == 80000
    assert result["balance_inr"] == 20000
    assert result["status"] == "Within entered budget"
    assert result["utilisation_pct"] == 80


def test_calculate_design_flags_over_budget():
    result = calculate_design(
        budget_inr=50000,
        selected={"drains": True},
        quantities={"drains": 2},
        rates_inr={"drains": 30000},
    )
    assert result["total_inr"] == 60000
    assert result["balance_inr"] == -10000
    assert result["status"] == "Over budget"


@pytest.mark.parametrize("budget", [-1, math.nan, math.inf, -math.inf, "bad"])
def test_calculate_design_rejects_invalid_budget(budget):
    with pytest.raises(ValueError):
        calculate_design(
            budget_inr=budget,
            selected={},
            quantities={},
            rates_inr={},
        )


@pytest.mark.parametrize("quantity", [0, -1, math.nan, math.inf, "bad"])
def test_calculate_design_rejects_invalid_quantity(quantity):
    with pytest.raises(ValueError):
        calculate_design(
            budget_inr=100000,
            selected={"drains": True},
            quantities={"drains": quantity},
            rates_inr={"drains": 1000},
        )


@pytest.mark.parametrize("rate", [-1, math.nan, math.inf, "bad"])
def test_calculate_design_rejects_invalid_rate(rate):
    with pytest.raises(ValueError):
        calculate_design(
            budget_inr=100000,
            selected={"drains": True},
            quantities={"drains": 1},
            rates_inr={"drains": rate},
        )


def test_unselected_components_are_not_costed():
    result = calculate_design(
        budget_inr=100000,
        selected={"drains": False, "garden": False},
        quantities={},
        rates_inr={},
    )
    assert result["line_items"] == []
    assert result["total_inr"] == 0
    assert result["component_count"] == 0


def test_zero_budget_has_no_utilisation_division_error():
    result = calculate_design(
        budget_inr=0,
        selected={"drains": True},
        quantities={"drains": 1},
        rates_inr={"drains": 0},
    )
    assert result["utilisation_pct"] is None
    assert result["status"] == "Within entered budget"


def test_review_items_only_include_selected_components():
    items = build_review_items({"drains": True, "garden": False})
    assert items
    assert all(item["component"] == "Underground drainage" for item in items)


def test_empty_selection_gets_general_review_prompt():
    items = build_review_items({})
    assert len(items) == 1
    assert "engineering review" in items[0]["check"].lower()


def test_compare_designs_reports_cost_delta_only():
    current = {"total_inr": 100000, "component_count": 2}
    alternative = {"total_inr": 125000, "component_count": 3}
    result = compare_designs(current, alternative)
    assert result["cost_difference_inr"] == 25000
    assert result["additional_components"] == 1
    assert result["interpretation"] == "Alternative costs more"


def test_shared_state_uses_custom_costs_for_budget_and_recommendations():
    from src.mitigation_intelligence import design_recommendations
    from src.smart_mitigation_studio import build_studio_state

    design = calculate_design(
        budget_inr=50000,
        selected={"drains": True},
        quantities={"drains": 2},
        rates_inr={"drains": 40000},
    )
    state = build_studio_state(
        project_name="Kochi test",
        area_type="Urban road",
        rainfall_mm_per_hour=50,
        budget_inr=50000,
        selected={"drains": True},
        design=design,
        site_area="Test road",
    )

    assert state["illustrative_component_cost_inr"] == 80000
    assert state["budget_balance_inr"] == -30000
    assert state["budget_status"] == "Over budget"
    assert state["site_area"] == "Test road"
    prompts = design_recommendations(state)
    assert any(item["Planning recommendation"] == "Review phasing and cost assumptions" for item in prompts)
