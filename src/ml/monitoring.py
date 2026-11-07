"""Input-range and deployment monitoring helpers.

These checks are descriptive.  They cannot detect every form of drift and they
do not validate a model.  Their purpose is to make out-of-range inference
visible rather than silently extrapolating.
"""

from __future__ import annotations

from typing import Any, Mapping

import math


def range_warnings(card: Mapping[str, Any], context: Mapping[str, Any]) -> list[str]:
    """Return warnings for values outside the observed training range."""
    ranges = card.get("feature_ranges")
    if not isinstance(ranges, Mapping):
        return ["No training feature ranges are recorded in the model card."]
    warnings: list[str] = []
    for name, value in context.items():
        bounds = ranges.get(name)
        if not isinstance(bounds, Mapping):
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(number):
            continue
        minimum = bounds.get("min")
        maximum = bounds.get("max")
        if isinstance(minimum, (int, float)) and number < minimum:
            warnings.append(
                f"{name}={number:g} is below the observed training minimum {minimum:g}."
            )
        if isinstance(maximum, (int, float)) and number > maximum:
            warnings.append(
                f"{name}={number:g} is above the observed training maximum {maximum:g}."
            )
    return warnings


def out_of_training_range_features(
    card: Mapping[str, Any], context: Mapping[str, Any]
) -> dict[str, dict[str, float]]:
    """Identify supplied numeric features outside the observed training envelope."""
    ranges = card.get("feature_ranges")
    if not isinstance(ranges, Mapping):
        return {}
    outside: dict[str, dict[str, float]] = {}
    for name, value in context.items():
        bounds = ranges.get(name)
        if not isinstance(bounds, Mapping):
            continue
        try:
            number = float(value)
            minimum = float(bounds.get("min"))
            maximum = float(bounds.get("max"))
        except (TypeError, ValueError, OverflowError):
            continue
        if not all(math.isfinite(item) for item in (number, minimum, maximum)):
            continue
        if number < minimum or number > maximum:
            outside[name] = {"value": number, "min": minimum, "max": maximum}
    return outside


def missingness_warnings(card: Mapping[str, Any], context: Mapping[str, Any]) -> list[str]:
    """Report features whose training missingness was high."""
    ranges = card.get("feature_ranges")
    if not isinstance(ranges, Mapping):
        return []
    warnings: list[str] = []
    for name, bounds in ranges.items():
        if not isinstance(bounds, Mapping):
            continue
        fraction = bounds.get("missing_fraction")
        if name in context and isinstance(fraction, (int, float)) and fraction >= 0.20:
            warnings.append(
                f"{name} was missing in {fraction:.0%} of training rows; its value has limited support."
            )
    return warnings


def monitoring_summary(cards: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarise registry-wide deployment caveats for the model lab."""
    statuses: dict[str, int] = {}
    for card in cards:
        status = str(card.get("status", "UNKNOWN"))
        statuses[status] = statuses.get(status, 0) + 1
    return {
        "n_models": len(cards),
        "status_counts": statuses,
        "validated_models": 0,
        "interpretation": (
            "No model is independently validated. Range checks are descriptive and "
            "do not establish fitness for operational use."
        ),
    }


__all__ = [
    "missingness_warnings",
    "monitoring_summary",
    "out_of_training_range_features",
    "range_warnings",
]
