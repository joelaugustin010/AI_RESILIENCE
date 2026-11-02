"""Shared, explainable mitigation-planning helpers for AI RESILIENCE.

All recommendations are transparent planning prompts. They do not estimate
flood probability, hydraulic performance, avoided damage, or risk reduction.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping


MODEL_VERSION = "1.0"

COMPONENT_CATALOG: dict[str, dict[str, Any]] = {
    "drains": {
        "name": "Underground drainage",
        "indicative_cost_inr": 150000,
        "group": "Water management",
    },
    "inlets": {
        "name": "Roadside stormwater inlets",
        "indicative_cost_inr": 50000,
        "group": "Water management",
    },
    "storage": {
        "name": "Stormwater storage pond",
        "indicative_cost_inr": 120000,
        "group": "Water management",
    },
    "garden": {
        "name": "Rain garden",
        "indicative_cost_inr": 60000,
        "group": "Green infrastructure",
    },
    "sensors": {
        "name": "Water-level sensors",
        "indicative_cost_inr": 40000,
        "group": "Monitoring",
    },
    "maintenance": {
        "name": "Maintenance access",
        "indicative_cost_inr": 30000,
        "group": "Operations",
    },
}

RAIN_CATEGORIES = (
    (30, "Low"),
    (70, "Moderate"),
    (110, "High"),
    (float("inf"), "Very high"),
)


def rainfall_category(rainfall_mm_per_hour: float) -> str:
    """Return the app's illustrative input band, not an official warning level."""
    value = float(rainfall_mm_per_hour)
    for upper_bound, label in RAIN_CATEGORIES:
        if value < upper_bound:
            return label
    return "Very high"


def build_design_state(
    *,
    project_name: str,
    area_type: str,
    rainfall_mm_per_hour: float,
    available_budget_inr: float,
    selected_components: Mapping[str, bool],
) -> dict[str, Any]:
    """Create the common, serializable design record used by both planning pages."""
    rainfall = float(rainfall_mm_per_hour)
    budget = float(available_budget_inr)
    if rainfall < 0 or rainfall > 150:
        raise ValueError("Rainfall input must be between 0 and 150 mm/hour.")
    if budget < 0:
        raise ValueError("Available budget cannot be negative.")

    selected = {
        key: bool(selected_components.get(key, False))
        for key in COMPONENT_CATALOG
    }
    selected_cost = sum(
        int(COMPONENT_CATALOG[key]["indicative_cost_inr"])
        for key, enabled in selected.items()
        if enabled
    )

    return {
        "model_version": MODEL_VERSION,
        "project_name": str(project_name).strip() or "Untitled mitigation concept",
        "location": "Kochi, Kerala, India",
        "area_type": str(area_type),
        "rainfall_input_mm_per_hour": rainfall,
        "rainfall_category": rainfall_category(rainfall),
        "available_budget_inr": budget,
        "selected_components": selected,
        "selected_component_names": [
            COMPONENT_CATALOG[key]["name"]
            for key, enabled in selected.items()
            if enabled
        ],
        "illustrative_component_cost_inr": selected_cost,
        "budget_balance_inr": budget - selected_cost,
        "budget_status": "Over budget" if selected_cost > budget else "Within entered budget",
        "cost_basis": "Illustrative planning values; not verified quotations",
        "engineering_status": "Concept only — qualified engineering review required",
    }


def design_recommendations(state: Mapping[str, Any]) -> list[dict[str, str]]:
    """Generate transparent prompts from user-selected inputs; never score effectiveness."""
    selected = state.get("selected_components", {})
    area_type = str(state.get("area_type", ""))
    rainfall = float(state.get("rainfall_input_mm_per_hour", 0))
    budget = float(state.get("available_budget_inr", 0))
    design_cost = float(state.get("illustrative_component_cost_inr", 0))
    category = rainfall_category(rainfall)
    recommendations: list[dict[str, str]] = []

    def add(priority: str, title: str, reason: str, next_step: str) -> None:
        recommendations.append({
            "Priority": priority,
            "Planning recommendation": title,
            "Why this was suggested": reason,
            "Suggested verification": next_step,
        })

    if rainfall >= 70 and not selected.get("drains", False):
        add(
            "High", "Review drainage inspection and capacity",
            f"The selected illustrative rainfall input is {rainfall:g} mm/hour ({category}), while underground drainage is not selected.",
            "Obtain a verified drainage asset inventory, condition survey and engineer-reviewed hydraulic assessment.",
        )
    if rainfall >= 70 and not selected.get("inlets", False):
        add(
            "Medium", "Review roadside inlet coverage",
            "The rainfall input is in the high or very-high planning band and roadside inlets are not included.",
            "Survey inlet locations, blockage history, catchment connections and maintenance responsibility.",
        )
    if rainfall >= 70 and not selected.get("storage", False):
        add(
            "Medium", "Assess whether stormwater storage merits study",
            "The rainfall input is in the high or very-high planning band and no storage component is selected.",
            "Check land availability, catchment flow, outfall constraints, environmental permissions and engineering feasibility.",
        )
    if "Low-lying" in area_type and not selected.get("garden", False):
        add(
            "Medium", "Review green-infrastructure opportunities",
            "The selected area type is low-lying and a rain-garden component is not selected.",
            "Check soil infiltration, groundwater, contamination, utilities and safe overflow routing before site selection.",
        )
    if rainfall >= 70 and not selected.get("sensors", False):
        add(
            "Medium", "Consider a monitoring and maintenance plan",
            "The rainfall input is in the high or very-high planning band and water-level monitoring is not selected.",
            "Define sensor purpose, siting, calibration, communications, alert ownership and maintenance arrangements.",
        )
    if selected.get("drains", False) and not selected.get("maintenance", False):
        add(
            "High", "Add an operations and maintenance review",
            "Drainage is selected but maintenance access is not included in this concept.",
            "Document safe inspection access, cleaning frequency, responsible operator and lifecycle costs.",
        )
    if budget > 0 and design_cost > budget:
        add(
            "High", "Review phasing and cost assumptions",
            f"The illustrative component total exceeds the entered budget by ₹{design_cost - budget:,.0f}.",
            "Obtain comparable quotations, confirm scope and lifecycle costs, then discuss phasing with the project owner.",
        )
    elif budget == 0:
        add(
            "Medium", "Enter a planning budget",
            "No available budget has been entered, so affordability cannot be reviewed.",
            "Enter an approved or clearly labelled provisional budget before comparing project costs.",
        )

    if not recommendations:
        add(
            "Review", "Complete local evidence and engineering checks",
            "No additional rule-based prompt was triggered by the current selections.",
            "Verify site conditions, project scope, costs, drainage data and maintenance responsibilities with qualified professionals.",
        )

    return recommendations


def review_project_register(
    project_rows: Iterable[Mapping[str, Any]],
    available_budget_inr: Any,
) -> dict[str, Any]:
    """Flag completeness issues in user-entered projects and report arithmetic only."""
    rows = list(project_rows)
    review_rows: list[dict[str, str]] = []
    known_total = 0.0
    unknown_costs = 0
    cost_values: list[float] = []

    for index, row in enumerate(rows, start=1):
        intervention = str(row.get("Intervention", "") or "").strip() or f"Project row {index}"
        issues: list[str] = []

        raw_cost = row.get("Cost INR")
        try:
            cost = float(raw_cost)
            if cost < 0:
                raise ValueError
            known_total += cost
            cost_values.append(cost)
        except (TypeError, ValueError):
            unknown_costs += 1
            issues.append("Cost missing or invalid")

        for field, label in (
            ("Location", "Location not specified"),
            ("Source / estimate date", "Cost source/date missing"),
            ("Scope and unit", "Scope/unit missing"),
            ("Evidence for risk reduction", "Supporting evidence not recorded"),
        ):
            if not str(row.get(field, "") or "").strip():
                issues.append(label)

        review_rows.append({
            "Project": intervention,
            "Review status": "Needs review" if issues else "Fields completed — verify evidence",
            "Items to review": "; ".join(issues) if issues else "No blank review fields detected",
        })

    try:
        budget = float(available_budget_inr)
        if budget < 0:
            budget = None
    except (TypeError, ValueError):
        budget = None

    within_budget = None
    if budget is not None and unknown_costs == 0:
        within_budget = known_total <= budget

    return {
        "project_count": len(rows),
        "known_cost_total_inr": known_total,
        "unknown_cost_count": unknown_costs,
        "budget_inr": budget,
        "remaining_budget_inr": budget - known_total if budget is not None else None,
        "within_budget": within_budget,
        "review_rows": review_rows,
        "interpretation": (
            "Completeness and arithmetic checks only. Blank fields do not prove a project is unsuitable, "
            "and completed fields do not verify evidence, feasibility, effectiveness or engineering safety."
        ),
    }
