"""Compatibility facade for the LLM-backed disaster assistant.

The old intent-classifier and template composer have been removed.  The
assistant now calls a configurable language-model provider and grounds project
answers with local retrieval over reviewed knowledge and module summaries.

For new code import from ``src.assistant.chat`` or ``src.assistant.config``.
This module keeps the stable names used by the Streamlit page and tests.
"""

from __future__ import annotations

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
    "chat_once",
    "configuration_help",
    "load_knowledge",
    "prepare_reply",
]
