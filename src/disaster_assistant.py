"""Small deterministic, source-grounded disaster information assistant.

It retrieves reviewed knowledge entries; it does not generate live warnings,
make local predictions, or infer unsupported causes or probabilities.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_PATH = ROOT / "data" / "disaster_knowledge.json"


class KnowledgeBaseError(ValueError):
    """Raised when the local disaster knowledge file is malformed."""


def load_knowledge(path: Path | None = None) -> list[dict[str, Any]]:
    """Load and validate the small local knowledge base."""
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
        for field in ("title", "summary", "keywords", "actions", "limitations", "sources"):
            if not topic.get(field):
                raise KnowledgeBaseError(f"Topic {topic_id!r} is missing {field}.")
        for source_record in topic["sources"]:
            parsed = urlparse(str(source_record.get("url", "")))
            if parsed.scheme != "https" or not parsed.netloc:
                raise KnowledgeBaseError(f"Topic {topic_id!r} has a non-HTTPS source URL.")
    return topics


def answer_question(question: str, topics: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Return the best keyword-matched knowledge entries and their evidence.

    Matching is transparent and deterministic. It is intentionally not called
    an LLM, a probability model, or an operational decision engine.
    """
    text = str(question or "").casefold().strip()
    if not text:
        return {
            "matched": False,
            "topics": [],
            "message": "Enter a disaster or preparedness question to search the reviewed knowledge base.",
        }
    knowledge = topics if topics is not None else load_knowledge()
    scored: list[tuple[int, dict[str, Any]]] = []
    for topic in knowledge:
        keywords = [str(word).casefold().strip() for word in topic.get("keywords", []) if str(word).strip()]
        hits = sum(1 for word in keywords if word in text)
        if hits:
            scored.append((hits, topic))
    if not scored:
        return {
            "matched": False,
            "topics": [],
            "message": (
                "No sufficiently close topic was found in the reviewed knowledge base. "
                "Try naming the hazard or service (for example, flood, cyclone, air pollution, or hospital continuity)."
            ),
        }
    scored.sort(key=lambda item: (-item[0], str(item[1].get("title", ""))))
    return {
        "matched": True,
        "topics": [
            {
                "id": topic["id"],
                "title": topic["title"],
                "summary": topic["summary"],
                "actions": list(topic["actions"]),
                "limitations": list(topic["limitations"]),
                "sources": list(topic["sources"]),
            }
            for _, topic in scored[:3]
        ],
        "message": "Results are retrieved from the project's reviewed knowledge file; they are not a live warning or local prediction.",
    }
