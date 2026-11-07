"""Compatibility facade for the LLM-backed disaster assistant.

The old intent-classifier and template composer have been removed.  The
assistant now calls a configurable language-model provider and grounds project
answers with local retrieval over reviewed knowledge and module summaries.

For new code import from ``src.assistant.chat`` or ``src.assistant.config``.
This module keeps the stable names used by the Streamlit page and tests.
"""

from __future__ import annotations

from typing import Any

from src.assistant.chat import (
    ReplyPlan,
    assistant_status,
    chat_once,
    configuration_help,
    prepare_reply,
)
from src.assistant.config import LLMConfigurationError
from src.assistant.knowledge import KNOWLEDGE_PATH, KnowledgeBaseError, load_knowledge
from src.assistant.llm import LLMRequestError

__all__ = [
    "KNOWLEDGE_PATH",
    "KnowledgeBaseError",
    "LLMConfigurationError",
    "LLMRequestError",
    "ReplyPlan",
    "assistant_status",
    "answer_question",
    "chat_once",
    "configuration_help",
    "load_knowledge",
    "prepare_reply",
]


def answer_question(
    question: str,
    topics: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return reviewed knowledge entries for legacy callers.

    This is a deprecated compatibility API retained for existing tests and
    downstream imports from the pre-LLM module.  The Streamlit assistant does
    not use it: live conversations go through ``prepare_reply`` and the
    configured LLM with RAG context.  Keeping this narrow adapter avoids
    breaking older integrations without making deterministic matching the
    chatbot's response engine.
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
        keywords = [
            str(word).casefold().strip()
            for word in topic.get("keywords", [])
            if str(word).strip()
        ]
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
        "message": (
            "Results are retrieved from the project's reviewed knowledge file; "
            "they are not a live warning or local prediction."
        ),
    }
