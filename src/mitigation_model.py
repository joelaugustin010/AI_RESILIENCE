"""Shared rules for mitigation component design and prioritisation.

This module keeps the budget planner and the smart design studio aligned on the
same mitigation catalog, cost assumptions, and explainable scoring logic.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

AREA_TYPES = [
    "Low-lying flood-prone area",
    "Urban road",
    "Residential neighbourhood",
    "Commercial area",
]

MITIGATION_COMPONENTS = [
    {
        "id": "drains",
        "title": "Underground drainage",
        "family": "Water management",
        "cost": 160000,
        "primary": 0.96,
        "secondary": 0.72,
        "benefit": 0.9,
        "risk_focus": "Drainage and conveyance",
        "description": "Conceptual underground conveyance and channel network for stormwater discharge.",
    },
    {
        "id": "inlets",
        "title": "Roadside stormwater inlets",
        "family": "Water management",
        "cost": 50000,
        "primary": 0.74,
        "secondary": 0.81,
        "benefit": 0.72,
        "risk_focus": "Road runoff collection",
        "description": "Collection points for road runoff and kerb drainage entry to the network.",
    },
    {
        "id": "storage",
        "title": "Stormwater storage pond",
        "family": "Storage",
        "cost": 130000,
        "primary": 0.9,
        "secondary": 0.77,
        "benefit": 0.85,
        "risk_focus": "Temporary detention",
        "description": "Temporary detention area for peak-event attenuation and controlled release.",
    },
    {
        "id": "garden",
        "title": "Rain garden",
        "family": "Green infrastructure",
        "cost": 60000,
        "primary": 0.68,
        "secondary": 0.88,
        "benefit": 0.81,
        "risk_focus": "Infiltration and treatment",
        "description": "Vegetated absorption zone that slows runoff and promotes infiltration.",
    },
    {
        "id": "sensors",
        "title": "Water-level sensors",
        "family": "Monitoring",
        "cost": 35000,
        "primary": 0.58,
        "secondary": 0.91,
        "benefit": 0.7,
        "risk_focus": "Monitoring and early warning",
        "description": "Flood monitoring points to improve situational awareness and maintenance triggers.",
    },
    {
        "id": "maintenance",
        "title": "Maintenance access",
        "family": "Operations",
        "cost": 30000,
        "primary": 0.62,
        "secondary": 0.86,
        "benefit": 0.75,
        "risk_focus": "Operational readiness",
        "description": "Access corridors and service points that support inspection and upkeep.",
    },
]

DEFAULT_SELECTION = {item["id"]: True for item in MITIGATION_COMPONENTS}


def get_component_catalog() -> list[dict[str, Any]]:
    """Return a stable catalog used by both planning surfaces."""
    return [dict(item) for item in MITIGATION_COMPONENTS]


def get_component_by_id(component_id: str) -> dict[str, Any]:
    for item in MITIGATION_COMPONENTS:
        if item["id"] == component_id:
            return dict(item)
    raise KeyError(f"Unknown mitigation component: {component_id}")


def selected_component_summary(selection: dict[str, bool]) -> list[dict[str, Any]]:
    selected = []
    for item in MITIGATION_COMPONENTS:
        if selection.get(item["id"], False):
            selected.append(dict(item))
    return selected


def scenario_profile(rainfall_mm_h: float, area_type: str) -> dict[str, float]:
    """Create transparent, non-engineering display values for design scenarios."""
    rainfall_fraction = max(0.0, min(float(rainfall_mm_h) / 150.0, 1.0))
    area_factor = {
        "Low-lying flood-prone area": 1.15,
        "Urban road": 1.02,
        "Residential neighbourhood": 0.96,
        "Commercial area": 1.08,
    }.get(area_type, 1.0)

    display_water_level = 0.35 + rainfall_fraction * 0.62 * area_factor
    pond_level = 0.32 + rainfall_fraction * 0.48 * area_factor
    flood_extent = 0.22 + rainfall_fraction * 0.68 * area_factor
    drainage_load = 0.35 + rainfall_fraction * 0.6
    return {
        "rainfall_fraction": rainfall_fraction,
        "display_water_level": display_water_level,
        "pond_level": pond_level,
        "flood_extent": flood_extent,
        "drainage_load": drainage_load,
    }


def evaluate_design_selection(selection: dict[str, bool], rainfall_mm_h: float, area_type: str) -> dict[str, Any]:
    """Score a design package using transparent assumptions only."""
    active = selected_component_summary(selection)
    total_cost = sum(item["cost"] for item in active)
    rainfall = scenario_profile(rainfall_mm_h, area_type)
    weights = {
        "drains": 0.26,
        "inlets": 0.12,
        "storage": 0.19,
        "garden": 0.14,
        "sensors": 0.11,
        "maintenance": 0.18,
    }

    score = 0.0
    for item in active:
        item_id = item["id"]
        rainfall_factor = 1.0 + rainfall["rainfall_fraction"] * 0.35
        score += item["benefit"] * weights.get(item_id, 0.1) * rainfall_factor

    score = max(0.0, min(score / 0.8, 1.0))
    resilience = round(score * 100, 1)
    budget_headroom = max(0.0, 1.0 - min(1.0, total_cost / 800000.0))
    recommended_actions = []
    if not selection.get("drains", False):
        recommended_actions.append("Add underground drainage to improve conveyance in heavier rainfall periods.")
    if not selection.get("storage", False):
        recommended_actions.append("Consider a detention or ponding feature to reduce peak runoff concentration.")
    if not selection.get("garden", False):
        recommended_actions.append("Introduce green infrastructure for infiltration and urban runoff reduction.")
    if not selection.get("sensors", False):
        recommended_actions.append("Add sensors to improve flood monitoring and trigger-based maintenance.")

    return {
        "selected_components": [item["id"] for item in active],
        "component_count": len(active),
        "component_total_cost": total_cost,
        "resilience_score": resilience,
        "budget_headroom": budget_headroom,
        "recommended_actions": recommended_actions,
        "scenario": rainfall,
    }


def prioritize_projects(projects: pd.DataFrame) -> pd.DataFrame:
    """Return a project table with a transparent composite score."""
    frame = projects.copy()
    frame["Cost INR"] = pd.to_numeric(frame.get("Cost INR", pd.Series(dtype=float)), errors="coerce")
    frame["Potential beneficiaries"] = pd.to_numeric(frame.get("Potential beneficiaries", pd.Series(dtype=float)), errors="coerce").fillna(0)
    frame["Priority"] = frame.get("Priority", pd.Series(dtype=str)).fillna("Medium").astype(str)
    frame["Priority Score"] = frame["Priority"].map({"High": 3, "Medium": 2, "Low": 1}).fillna(2)
    frame["Cost score"] = frame["Cost INR"].fillna(0).map(lambda v: 1.0 if v <= 150000 else 0.6 if v <= 500000 else 0.25)
    frame["Benefit score"] = frame["Potential beneficiaries"].fillna(0).map(lambda v: min(1.0, v / 5000.0))
    frame["Decision score"] = (
        frame["Priority Score"] * 0.35
        + frame["Cost score"] * 0.25
        + frame["Benefit score"] * 0.40
    )
    frame["Decision score"] = frame["Decision score"].clip(0, 1)
    return frame.sort_values("Decision score", ascending=False).reset_index(drop=True)


def build_implementation_plan(projects: pd.DataFrame, budget: float) -> pd.DataFrame:
    """Recommend a phased implementation plan within budget without claiming optimality."""
    ranked = prioritize_projects(projects)
    ranked = ranked[ranked.get("Cost INR", pd.Series(dtype=float)).notna()].copy()
    ranked = ranked[ranked["Cost INR"] > 0].copy()
    ranked = ranked.sort_values("Decision score", ascending=False).reset_index(drop=True)
    phases = []
    remaining = float(budget)
    for _, row in ranked.iterrows():
        if remaining <= 0:
            break
        cost = float(row["Cost INR"])
        if cost <= remaining:
            phase = "Phase 1"
        else:
            phase = "Phase 2"
        phases.append({
            "Project": row.get("Intervention", "Unnamed project"),
            "Location": row.get("Location", ""),
            "Cost INR": cost,
            "Priority": row.get("Priority", "Medium"),
            "Decision score": round(float(row["Decision score"]), 3),
            "Implementation phase": phase,
        })
        remaining -= min(cost, remaining)
    return pd.DataFrame(phases)


def minimum_viable_package() -> dict[str, Any]:
    package = {item["id"]: True for item in MITIGATION_COMPONENTS if item["id"] in {"drains", "storage", "garden"}}
    package["inlets"] = True
    package["maintenance"] = True
    return package


DEFAULT_DESIGN_STATE = {
    "project_name": "Kochi Urban Flood Management Concept",
    "area_type": "Residential neighbourhood",
    "available_budget": 500000,
    "rainfall_mm_h": 50,
    "components": {item["id"]: True for item in MITIGATION_COMPONENTS},
}


__all__ = [
    "AREA_TYPES",
    "DEFAULT_DESIGN_STATE",
    "DEFAULT_SELECTION",
    "MITIGATION_COMPONENTS",
    "build_implementation_plan",
    "evaluate_design_selection",
    "get_component_by_id",
    "get_component_catalog",
    "minimum_viable_package",
    "prioritize_projects",
    "scenario_profile",
    "selected_component_summary",
]
