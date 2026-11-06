"""Atomic persistence for model artifacts, cards and the shared registry."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from src.ml.paths import (
    REGISTRY_PATH,
    ROOT,
    artifact_path,
    card_path,
    model_dir,
)

try:  # joblib is a scikit-learn dependency but is imported explicitly here.
    import joblib
except ImportError as exc:  # pragma: no cover - deployment dependency failure
    raise RuntimeError("joblib is required to persist shared ML models.") from exc


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def write_json(path: Path, payload: Any) -> None:
    """Write deterministic, UTF-8 JSON via a temporary file."""
    _atomic_write_text(path, json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n")


def read_json(path: Path, *, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def save_model_bundle(
    model_id: str,
    pipeline: Any,
    card: dict[str, Any],
    *,
    compress: int = 3,
) -> dict[str, str]:
    """Persist the fitted pipeline and card, returning relative paths."""
    directory = model_dir(model_id)
    directory.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, artifact_path(model_id), compress=compress)
    write_json(card_path(model_id), card)
    return {
        "artifact": str(artifact_path(model_id).relative_to(ROOT)),
        "card": str(card_path(model_id).relative_to(ROOT)),
    }


def load_artifact(model_id: str) -> Any:
    path = artifact_path(model_id)
    if not path.exists():
        raise FileNotFoundError(f"No saved artifact for model {model_id!r} at {path}.")
    return joblib.load(path)


def load_card_file(model_id: str) -> dict[str, Any] | None:
    return read_json(card_path(model_id))


def write_registry(cards: Iterable[dict[str, Any]], *, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    """Write the shared registry from model cards."""
    ordered = sorted(cards, key=lambda card: str(card.get("model_id", "")))
    payload = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "models": ordered,
        "n_models": len(ordered),
    }
    if extra:
        payload.update(extra)
    write_json(REGISTRY_PATH, payload)
    return payload


__all__ = [
    "load_artifact",
    "load_card_file",
    "read_json",
    "save_model_bundle",
    "write_json",
    "write_registry",
]
