import pytest

from src.mitigation_optimizer import optimize_portfolio


def test_optimizer_maximises_planner_points_within_budget():
    projects = [
        {"name": "Drainage", "cost_inr": 60, "value_points": 8},
        {"name": "Rain garden", "cost_inr": 40, "value_points": 5},
        {"name": "Sensor", "cost_inr": 30, "value_points": 4},
    ]
    result = optimize_portfolio(projects, 100)
    assert {item["name"] for item in result["selected"]} == {"Drainage", "Rain garden"}
    assert result["total_value_points"] == 13
    assert result["total_cost_inr"] == 100
    assert result["remaining_budget_inr"] == 0


def test_optimizer_tie_breaks_on_lower_cost():
    projects = [
        {"name": "A", "cost_inr": 90, "value_points": 7},
        {"name": "B", "cost_inr": 70, "value_points": 7},
    ]
    result = optimize_portfolio(projects, 100)
    assert [item["name"] for item in result["selected"]] == ["B"]


def test_optimizer_returns_empty_when_nothing_fits():
    result = optimize_portfolio([{"name": "A", "cost_inr": 101, "value_points": 5}], 100)
    assert result["selected"] == []
    assert result["total_value_points"] == 0


@pytest.mark.parametrize("budget", [-1, float("nan"), float("inf")])
def test_optimizer_rejects_invalid_budget(budget):
    with pytest.raises(ValueError):
        optimize_portfolio([], budget)


def test_optimizer_caps_exact_search_size():
    projects = [{"name": str(i), "cost_inr": 1, "value_points": 1} for i in range(19)]
    with pytest.raises(ValueError, match="At most 18"):
        optimize_portfolio(projects, 100)
