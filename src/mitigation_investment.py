"""Transparent, human-assessed mitigation investment prioritisation.

Scores organise supplied planning judgements; they are not ML predictions,
engineering assessments, or measured intervention effectiveness.
"""
from __future__ import annotations

from typing import Any, Mapping

CRITERIA = {
    "Site risk severity (1–5)": ("site_risk_severity", 0.35),
    "Urgency (1–5)": ("urgency", 0.25),
    "Evidence strength (1–5)": ("evidence_strength", 0.20),
    "Implementation readiness (1–5)": ("implementation_readiness", 0.20),
}


def score_investment_priority(project: Mapping[str, Any]) -> dict[str, Any]:
    """Score a project only when all four explicit human assessments exist.

    Each 1–5 input is normalised to 0–100 and weighted. Missing or invalid
    inputs produce an unscored result rather than an assumed default.
    """
    values: dict[str, int] = {}
    missing: list[str] = []
    for label, (field, _weight) in CRITERIA.items():
        raw = project.get(field)
        try:
            numeric = int(raw)
            if isinstance(raw, bool) or numeric < 1 or numeric > 5 or float(raw) != numeric:
                raise ValueError
        except (TypeError, ValueError, OverflowError):
            missing.append(label)
            continue
        values[field] = numeric

    if missing:
        return {
            "score": None,
            "band": "Not scored",
            "criteria": values,
            "missing": missing,
            "explanation": "Complete all four documented assessments before comparing this project.",
        }

    score = sum(
        ((values[field] - 1) / 4) * 100 * weight
        for field, weight in CRITERIA.values()
    )
    score = round(score, 1)
    if score >= 70:
        band = "Higher assessed priority"
    elif score >= 40:
        band = "Moderate assessed priority"
    else:
        band = "Further review"
    return {
        "score": score,
        "band": band,
        "criteria": values,
        "missing": [],
        "explanation": (
            "Weighted human assessment: site risk 35%, urgency 25%, "
            "evidence strength 20%, implementation readiness 20%."
        ),
    }
