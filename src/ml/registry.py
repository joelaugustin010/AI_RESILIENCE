"""Model-card registry and consistency checks."""

from __future__ import annotations

from typing import Any, Iterable

from src.ml.paths import MODELS_ROOT, REGISTRY_PATH
from src.ml.persistence import load_card_file, read_json, write_registry

REQUIRED_CARD_FIELDS: tuple[str, ...] = (
    "model_id",
    "hazard",
    "status",
    "validation_status",
    "feature_columns",
    "target_definition",
    "metrics",
    "limitations",
    "intended_use",
    "prohibited_use",
)


def _scan_cards() -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    if not MODELS_ROOT.exists():
        return cards
    for path in sorted(MODELS_ROOT.glob("*/model_card.json")):
        card = read_json(path)
        if isinstance(card, dict) and card.get("model_id"):
            cards.append(card)
    return cards


def list_model_cards() -> list[dict[str, Any]]:
    """Return registry cards, falling back to scanning model directories.

    A missing registry is not an error: the application can still show that no
    models are available.  Corrupt or partial cards are skipped rather than
    presented as valid.
    """
    registry = read_json(REGISTRY_PATH, default={})
    cards = registry.get("models") if isinstance(registry, dict) else None
    if isinstance(cards, list):
        valid = [card for card in cards if isinstance(card, dict) and card.get("model_id")]
        if valid:
            return valid
    return _scan_cards()


def load_model_card(model_id: str) -> dict[str, Any] | None:
    """Load a single model card, checking the registry fallback."""
    if not model_id:
        return None
    card = load_card_file(model_id)
    if isinstance(card, dict) and card.get("model_id") == model_id:
        return card
    for candidate in list_model_cards():
        if candidate.get("model_id") == model_id:
            return candidate
    return None


def card_consistency_problems(card: dict[str, Any]) -> list[str]:
    """Return problems that make a card unusable for inference or reporting."""
    problems: list[str] = []
    for name in REQUIRED_CARD_FIELDS:
        if name not in card:
            problems.append(f"Missing required field {name!r}.")
    features = card.get("feature_columns")
    if not isinstance(features, list) or not features:
        problems.append("feature_columns must be a non-empty list.")
    elif any(not isinstance(item, str) for item in features):
        problems.append("feature_columns must contain strings.")
    if card.get("target_column") in set(features or []):
        problems.append("The target column appears in feature_columns.")
    if not isinstance(card.get("metrics"), dict):
        problems.append("metrics must be a mapping.")
    if not isinstance(card.get("limitations"), list) or not card.get("limitations"):
        problems.append("limitations must be a non-empty list.")
    if card.get("status") not in {
        "NO_SKILL",
        "WEAK_RESEARCH_SIGNAL",
        "RESEARCH_SIGNAL_NOT_VALIDATED",
        "EXPLORATORY_ASSOCIATION",
        "INSUFFICIENT_TEST_EVENTS",
    }:
        problems.append(f"Unrecognised status {card.get('status')!r}.")
    if card.get("validation_status") != "SINGLE_TEMPORAL_HOLDOUT_NOT_INDEPENDENTLY_VALIDATED":
        problems.append("Cards must state the single-holdout validation boundary.")
    return problems


def cards_by_hazard() -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for card in list_model_cards():
        grouped.setdefault(str(card.get("hazard")), []).append(card)
    return grouped


def register(cards: Iterable[dict[str, Any]], *, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    """Validate and write the registry."""
    valid: list[dict[str, Any]] = []
    for card in cards:
        problems = card_consistency_problems(card)
        if problems:
            raise ValueError(
                f"Model card {card.get('model_id')!r} is inconsistent: {problems}"
            )
        valid.append(card)
    return write_registry(valid, extra=extra)


__all__ = [
    "REQUIRED_CARD_FIELDS",
    "card_consistency_problems",
    "cards_by_hazard",
    "list_model_cards",
    "load_model_card",
    "register",
]
