"""Retrieval-augmented generation (RAG) helpers.

The retrieval index is local TF-IDF over reviewed knowledge topics and
read-only summaries from the application modules.  Retrieval selects evidence;
it never writes the answer.  The language model receives the retrieved records
as context and generates the response itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from src.assistant.corpus import default_retrieval_index

MAX_CONTEXT_CHARS = 6000
MAX_CHUNK_TEXT = 900


@dataclass(frozen=True)
class Evidence:
    id: str
    title: str
    text: str
    facts: tuple[str, ...]
    limitations: tuple[str, ...]
    sources: tuple[dict[str, str], ...]
    evidence_status: str
    score: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "text": self.text,
            "facts": list(self.facts),
            "limitations": list(self.limitations),
            "sources": [dict(source) for source in self.sources],
            "evidence_status": self.evidence_status,
            "score": round(self.score, 4),
        }


def _retrieval_query(question: str, history: Iterable[dict[str, Any]] | None) -> str:
    parts = [str(question or "").strip()]
    recent = [item for item in (history or []) if item.get("content")]
    for item in recent[-2:]:
        content = str(item.get("content", "")).strip()
        if content:
            parts.append(content[:350])
    return " ".join(parts).strip()


def retrieve(
    question: str,
    history: Iterable[dict[str, Any]] | None = None,
    *,
    limit: int = 6,
    min_score: float = 0.08,
) -> list[Evidence]:
    """Return the most relevant project records for a question."""
    query = _retrieval_query(question, history)
    if not query:
        return []
    try:
        index = default_retrieval_index()
        results = index.search(query, limit=max(limit * 3, limit))
    except Exception:
        # Retrieval is an enhancement.  A malformed project file must not make
        # general conversation impossible.
        return []

    evidence: list[Evidence] = []
    seen: set[str] = set()
    for item in results:
        chunk = item["chunk"]
        chunk_id = str(chunk.get("id", ""))
        if not chunk_id or chunk_id in seen:
            continue
        # ``score`` includes a hand-set record priority.  Relevance must be
        # judged on the raw cosine similarity so a high-priority safety record
        # is not injected into unrelated general-knowledge questions.
        score = float(item.get("raw_score", item.get("score", 0.0)))
        if score < min_score:
            continue
        seen.add(chunk_id)
        evidence.append(
            Evidence(
                id=chunk_id,
                title=str(chunk.get("title", "Project record")),
                text=str(chunk.get("text", "")),
                facts=tuple(str(fact) for fact in chunk.get("facts", []) if str(fact).strip()),
                limitations=tuple(
                    str(item) for item in chunk.get("limitations", []) if str(item).strip()
                ),
                sources=tuple(
                    {
                        "publisher": str(source.get("publisher", "Source")),
                        "title": str(source.get("title", "Source record")),
                        "url": str(source.get("url", "")),
                    }
                    for source in chunk.get("sources", [])
                    if source.get("url")
                ),
                evidence_status=str(chunk.get("evidence_status", "Status not stated")),
                score=score,
            )
        )
        if len(evidence) >= limit:
            break
    return evidence


def collect_sources(evidence: Iterable[Evidence]) -> list[dict[str, str]]:
    """Collect unique, displayable sources from retrieved evidence."""
    sources: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in evidence:
        for source in item.sources:
            key = (source.get("publisher", ""), source.get("url", ""))
            if key in seen or not source.get("url"):
                continue
            seen.add(key)
            sources.append(dict(source))
    return sources


def format_context(evidence: Iterable[Evidence]) -> str:
    """Format retrieved records as a compact evidence block for the LLM."""
    blocks: list[str] = []
    total = 0
    for index, item in enumerate(evidence, start=1):
        facts = "\n".join(f"- {fact}" for fact in item.facts[:4])
        limitations = "\n".join(f"- {note}" for note in item.limitations[:2])
        sources = "\n".join(
            f"- {source.get('publisher', 'Source')}: {source.get('title', '')} ({source.get('url', '')})"
            for source in item.sources[:2]
        )
        text = item.text[:MAX_CHUNK_TEXT]
        block = (
            f"[{index}] {item.title} (id: {item.id})\n"
            f"Evidence status: {item.evidence_status}\n"
            f"Retrieval score: {item.score:.3f}\n"
            f"Record text: {text}\n"
            f"{'Key facts:' + chr(10) + facts if facts else ''}\n"
            f"{'Limitations:' + chr(10) + limitations if limitations else ''}\n"
            f"{'Sources:' + chr(10) + sources if sources else ''}"
        ).strip()
        if total + len(block) > MAX_CONTEXT_CHARS:
            break
        blocks.append(block)
        total += len(block)
    return "\n\n".join(blocks)


__all__ = [
    "Evidence",
    "collect_sources",
    "format_context",
    "retrieve",
]
