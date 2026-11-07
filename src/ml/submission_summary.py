"""Pure ranking helpers for the evaluator-facing ML evidence page."""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any


def _finite_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def rank_regression_cards(cards: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Return regression cards with a recorded finite MAE-skill score, best first.

    The legacy metric key is retained in persisted cards, but the comparator is
    read from each card and may be persistence or a constant no-change baseline."""
    ranked: list[dict[str, Any]] = []
    for card in cards:
        if card.get("task_type") != "regression":
            continue
        metrics = card.get("metrics")
        if not isinstance(metrics, Mapping):
            continue
        skill = metrics.get("mae_skill_over_persistence")
        if not _finite_number(skill):
            continue
        ranked.append(dict(card))
    return sorted(
        ranked,
        key=lambda card: (
            -float(card["metrics"]["mae_skill_over_persistence"]),
            str(card.get("model_id", "")),
        ),
    )


def rank_classifier_cards(cards: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Rank classifier cards by absolute F1 gain over their recorded persistence baseline."""
    ranked: list[dict[str, Any]] = []
    for card in cards:
        if card.get("task_type") == "regression":
            continue
        metrics = card.get("metrics")
        if not isinstance(metrics, Mapping):
            continue
        baseline = metrics.get("persistence_baseline")
        if not isinstance(baseline, Mapping):
            continue
        f1 = metrics.get("f1")
        baseline_f1 = baseline.get("f1")
        if not (_finite_number(f1) and _finite_number(baseline_f1)):
            continue
        ranked.append(dict(card))
    return sorted(
        ranked,
        key=lambda card: (
            -(
                float(card["metrics"]["f1"])
                - float(card["metrics"]["persistence_baseline"]["f1"])
            ),
            str(card.get("model_id", "")),
        ),
    )


def regression_baseline_label(card: Mapping[str, Any]) -> str:
    """Describe the comparator actually recorded for a regression card."""
    metrics = card.get("metrics")
    baseline = metrics.get("persistence_baseline") if isinstance(metrics, Mapping) else None
    baseline_type = baseline.get("type") if isinstance(baseline, Mapping) else None
    if baseline_type == "constant_no_change":
        return "No-change baseline"
    if baseline_type == "persistence":
        return "Persistence baseline"
    return "Recorded baseline"


__all__ = ["rank_classifier_cards", "rank_regression_cards", "regression_baseline_label"]
