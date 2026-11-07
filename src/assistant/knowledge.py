"""Validation and loading for the reviewed disaster knowledge file."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_PATH = ROOT / "data" / "disaster_knowledge.json"

REQUIRED_TOPIC_FIELDS = ("title", "summary", "keywords", "actions", "limitations", "sources")


class KnowledgeBaseError(ValueError):
    """Raised when the local disaster knowledge file is malformed."""


def load_knowledge(path: Path | None = None) -> list[dict[str, Any]]:
    """Load and validate the local reviewed knowledge base.

    The schema check is deliberately strict so a malformed or unreviewed entry
    cannot silently enter retrieval.  It does not certify the scientific
    validity of an entry; provenance and limitations remain part of each record.
    """
    source = Path(path) if path is not None else KNOWLEDGE_PATH
    try:
        document = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise KnowledgeBaseError(f"Could not load disaster knowledge: {exc}") from exc
    topics = document.get("topics") if isinstance(document, dict) else None
    if not isinstance(topics, list) or not topics:
        raise KnowledgeBaseError("Knowledge file must contain a non-empty topics list.")
    seen_ids: set[str] = set()
    for topic in topics:
        if not isinstance(topic, dict):
            raise KnowledgeBaseError("Each topic must be an object.")
        topic_id = str(topic.get("id", "")).strip()
        if not topic_id or topic_id in seen_ids:
            raise KnowledgeBaseError("Topic IDs must be present and unique.")
        seen_ids.add(topic_id)
        for field in REQUIRED_TOPIC_FIELDS:
            if not topic.get(field):
                raise KnowledgeBaseError(f"Topic {topic_id!r} is missing {field}.")
        if not isinstance(topic["keywords"], list) or not all(isinstance(item, str) for item in topic["keywords"]):
            raise KnowledgeBaseError(f"Topic {topic_id!r} has malformed keywords.")
        for list_field in ("actions", "limitations"):
            if not isinstance(topic[list_field], list) or not all(isinstance(item, str) for item in topic[list_field]):
                raise KnowledgeBaseError(f"Topic {topic_id!r} has malformed {list_field}.")
        for source_record in topic["sources"]:
            parsed = urlparse(str(source_record.get("url", "")))
            if parsed.scheme != "https" or not parsed.netloc:
                raise KnowledgeBaseError(f"Topic {topic_id!r} has a non-HTTPS source URL.")
    return topics


__all__ = ["KnowledgeBaseError", "KNOWLEDGE_PATH", "load_knowledge"]
