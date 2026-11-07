"""LLM-backed disaster assistant with retrieval-augmented project evidence.

The assistant calls a configurable language-model API and uses local retrieval
over reviewed project knowledge.  It does not contain a canned response
database.  Imports are lazy so lightweight helpers do not load the index.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "assistant_status",
    "chat_once",
    "configuration_help",
    "prepare_reply",
]


def __getattr__(name: str) -> Any:
    if name in {"assistant_status", "chat_once", "prepare_reply", "configuration_help"}:
        from src.assistant import chat

        return getattr(chat, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
