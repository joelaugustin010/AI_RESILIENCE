"""Transparent calculations for the Smart Mitigation Design Studio.

The functions in this module calculate user-entered planning allowances only.
They do not model hydraulics, flood depth, avoided damage or intervention efficacy.
"""
from __future__ import annotations

import math
from typing import Any, Mapping

from src.mitigation_intelligence import COMPONENT_CATALOG


COMPONENT_DETAILS = {
    "drains": {"unit": "package", "default_quantity": 1, "label": "Underground drainage"},
    "inlets": {"unit": "units", "default_quantity": 1, "label": "Roadside stormwater inlets"},
    "storage": {"unit": "package", "default_quantity": 1, "label": "Stormwater storage pond"},
    "garden": {"unit": "site", "default_quantity": 1, "label": "Rain garden / green infrastructure"},
    "sensors": {"unit": "units", "default_quantity": 1, "label": "Water-level monitoring sensors"},
    "maintenance": {"unit": "package", "default_quantity": 1, "label": "Maintenance access and provision"},
}

REVIEW_CHECKS = {
    "drains": [
        "Drainage asset survey and invert levels checked",
        "Downstream outfall capacity and tidal/backwater constraints reviewed",
        "Utility conflicts and right-of-way permissions checked",
    ],
    "inlets": [
        "Inlet spacing, road gradients and catchment connections surveyed",
        "Blockage history and cleaning responsibility documented",
    ],
    "storage": [
        "Land ownership, available footprint and safe overflow route confirmed",
        "Storage volume and outlet controls calculated by an engineer",
    ],
    "garden": [
        "Soil infiltration, groundwater and contamination assessed",
        "Overflow route and long-term landscape maintenance defined",
    ],
    "sensors": [
        "Sensor purpose, siting, power and communications specified",
        "Calibration, alert ownership and maintenance plan documented",
    ],
    "maintenance": [
        "Named operating agency and inspection schedule identified",
        "Lifecycle and recurring maintenance costs included",
    ],
}


def calculate_design(
    *,
    budget_inr: float,
    selected: Mapping[str, bool],
    quantities: Mapping[str, float],
    rates_inr: Mapping[str, float],
) -> dict[str, Any]:
    """Calculate a transparent line-item estimate and budget balance."""
    try:
        budget = float(budget_inr)
    except (TypeError, ValueError):
        raise ValueError("Budget must be a valid non-negative number.")
    if not math.isfinite(budget) or budget < 0:
        raise ValueError("Budget must be a valid non-negative number.")

    rows = []
    total = 0.0
    for key, details in COMPONENT_DETAILS.items():
        if not selected.get(key, False):
            continue
        try:
            quantity = float(quantities.get(key, details["default_quantity"]))
            rate = float(rates_inr.get(key, COMPONENT_CATALOG[key]["indicative_cost_inr"]))
        except (TypeError, ValueError):
            raise ValueError(f"Quantity and rate for {details['label']} must be numeric.")
        if not math.isfinite(quantity) or quantity <= 0:
            raise ValueError(f"Quantity for {details['label']} must be greater than zero.")
        if not math.isfinite(rate) or rate < 0:
            raise ValueError(f"Rate for {details['label']} must be non-negative.")
        line_total = quantity * rate
        total += line_total
        rows.append({
            "key": key,
            "component": details["label"],
            "unit": details["unit"],
            "quantity": quantity,
            "rate_inr": rate,
            "estimated_cost_inr": line_total,
            "basis": "User-entered planning allowance; quotation not verified",
        })

    return {
        "line_items": rows,
        "component_count": len(rows),
        "total_inr": total,
        "budget_inr": budget,
        "balance_inr": budget - total,
        "status": "Over budget" if total > budget else "Within entered budget",
        "utilisation_pct": (total / budget * 100) if budget > 0 else None,
    }


def build_review_items(selected: Mapping[str, bool]) -> list[dict[str, str]]:
    """Return review prompts relevant to selected components."""
    items = []
    for key, checks in REVIEW_CHECKS.items():
        if selected.get(key, False):
            for check in checks:
                items.append({"component": COMPONENT_DETAILS[key]["label"], "check": check})
    if not items:
        items.append({
            "component": "Project",
            "check": "Select at least one intervention and obtain a site-specific engineering review.",
        })
    return items


def compare_designs(current: Mapping[str, Any], alternative: Mapping[str, Any]) -> dict[str, Any]:
    """Compare cost and component count only; no effectiveness score is implied."""
    delta = float(alternative["total_inr"]) - float(current["total_inr"])
    return {
        "cost_difference_inr": delta,
        "additional_components": int(alternative["component_count"]) - int(current["component_count"]),
        "interpretation": (
            "Alternative costs more" if delta > 0
            else "Alternative costs less" if delta < 0
            else "Both options have the same estimated cost"
        ),
    }
