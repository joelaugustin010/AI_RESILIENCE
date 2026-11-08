"""Transparent budget-constrained portfolio scenario optimisation.

The optimiser maximises supplied integer priority points from a transparent,
human-assessed investment score. It does not estimate hazard reduction,
avoided losses, social benefit, or public funding priority.
"""
from __future__ import annotations

import math
from typing import Any


def optimize_portfolio(
    projects: list[dict[str, Any]], budget_inr: float, max_projects: int = 18
) -> dict[str, Any]:
    """Return the best affordable project subset for supplied priority points.

    Objective: maximise the sum of integer priority points from explicit
    human assessments. Tie-break: minimise total cost. Each project can be
    selected at most once.
    """
    budget = float(budget_inr)
    if not math.isfinite(budget) or budget < 0:
        raise ValueError("Budget must be a finite, non-negative amount.")
    if len(projects) > max_projects:
        raise ValueError(f"At most {max_projects} projects can be compared exactly.")

    clean: list[dict[str, Any]] = []
    for project in projects:
        try:
            cost = float(project["cost_inr"])
            points = int(project["value_points"])
            name = str(project["name"]).strip()
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            raise ValueError("Each project needs a name, cost_inr and integer value_points.") from exc
        if not name or not math.isfinite(cost) or cost <= 0:
            raise ValueError("Project names and costs must be valid; costs must be positive.")
        if points < 1:
            raise ValueError("Planner value points must be at least 1.")
        clean.append({"name": name, "cost_inr": cost, "value_points": points})

    best: list[dict[str, Any]] = []
    best_points = 0
    best_cost = 0.0
    count = len(clean)

    # Exhaustive exact search is deliberately capped to keep runtime predictable.
    for mask in range(1, 1 << count):
        chosen = [clean[i] for i in range(count) if mask & (1 << i)]
        total_cost = sum(item["cost_inr"] for item in chosen)
        if total_cost > budget:
            continue
        total_points = sum(item["value_points"] for item in chosen)
        if (total_points > best_points or
                (total_points == best_points and total_points > 0 and total_cost < best_cost)):
            best = chosen
            best_points = total_points
            best_cost = total_cost

    return {
        "selected": best,
        "total_value_points": best_points,
        "total_cost_inr": best_cost,
        "remaining_budget_inr": budget - best_cost,
        "method": "Exact exhaustive 0/1 subset search",
        "objective": "Maximise human-assessed priority points; minimise cost on ties",
    }
