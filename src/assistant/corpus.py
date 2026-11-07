"""Build the retrieval corpus from reviewed knowledge and live project modules."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any, Iterable

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import FeatureUnion

from src.assistant.context import all_module_context
from src.assistant.knowledge import load_knowledge

_WORD = re.compile(r"[a-z0-9][a-z0-9\.\-/]*")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def normalize_text(value: object) -> str:
    text = str(value or "").casefold()
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9µ\.\-/ ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _topic_id(topic: dict[str, Any]) -> str:
    return str(topic.get("id", "")).strip()


def _topic_sources(topic: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "publisher": str(source.get("publisher", "Source")),
            "title": str(source.get("title", "Source record")),
            "url": str(source.get("url", "")),
        }
        for source in topic.get("sources", [])
        if source.get("url")
    ]


def build_knowledge_chunks(topics: Iterable[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Turn each reviewed topic into summary, action and limitation chunks."""
    knowledge = list(topics) if topics is not None else load_knowledge()
    chunks: list[dict[str, Any]] = []
    for topic in knowledge:
        topic_id = _topic_id(topic)
        title = str(topic.get("title", topic_id))
        summary = str(topic.get("summary", ""))
        actions = [str(item) for item in topic.get("actions", [])]
        limitations = [str(item) for item in topic.get("limitations", [])]
        keywords = [str(item) for item in topic.get("keywords", [])]
        sources = _topic_sources(topic)
        base = {
            "topic_ids": (topic_id,),
            "kind": "knowledge_topic",
            "evidence_status": "Reviewed preparedness guidance",
            "sources": sources,
            "limitations": limitations,
            "priority": 0.3,
        }
        chunks.append({
            **base,
            "id": f"knowledge:{topic_id}:summary",
            "title": title,
            "text": " ".join([title, summary, " ".join(keywords)]),
            "facts": [summary],
        })
        if actions:
            chunks.append({
                **base,
                "id": f"knowledge:{topic_id}:actions",
                "title": f"{title}: preparedness actions",
                "text": " ".join([title, "preparedness actions", *actions]),
                "facts": actions,
            })
        if limitations:
            chunks.append({
                **base,
                "id": f"knowledge:{topic_id}:limitations",
                "title": f"{title}: data limitations",
                "text": " ".join([title, "limitations uncertainty data gaps", *limitations]),
                "facts": limitations,
            })
    return chunks


@lru_cache(maxsize=1)
def _default_module_chunks() -> tuple[dict[str, Any], ...]:
    return tuple(all_module_context())


def build_chunks(topics: Iterable[dict[str, Any]] | None = None, *, include_modules: bool = True) -> list[dict[str, Any]]:
    chunks = build_knowledge_chunks(topics)
    if include_modules:
        chunks.extend(dict(item) for item in _default_module_chunks())
    # Stable de-duplication by id.
    seen: set[str] = set()
    result = []
    for chunk in chunks:
        chunk_id = str(chunk.get("id", ""))
        if not chunk_id or chunk_id in seen:
            continue
        seen.add(chunk_id)
        result.append(chunk)
    return result


def _vectorizer() -> FeatureUnion:
    return FeatureUnion([
        ("word", TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            stop_words="english",
            sublinear_tf=True,
            min_df=1,
            max_features=40000,
        )),
        ("char", TfidfVectorizer(
            lowercase=True,
            analyzer="char_wb",
            ngram_range=(3, 5),
            sublinear_tf=True,
            min_df=1,
            max_features=50000,
        )),
    ])


class RetrievalIndex:
    """Small in-memory TF-IDF index over evidence chunks and their sentences."""

    def __init__(self, chunks: list[dict[str, Any]]) -> None:
        self.chunks = chunks
        self.documents = [normalize_text(f"{chunk.get('title', '')} {chunk.get('text', '')}") for chunk in chunks]
        self.vectorizer = _vectorizer()
        self.matrix = self.vectorizer.fit_transform(self.documents)
        sentence_rows: list[tuple[int, str]] = []
        for chunk_index, chunk in enumerate(chunks):
            for value in [chunk.get("text", ""), *chunk.get("facts", [])]:
                for sentence in _SENTENCE_SPLIT.split(str(value)):
                    sentence = sentence.strip()
                    if len(sentence) >= 25:
                        sentence_rows.append((chunk_index, sentence))
        self.sentence_rows = sentence_rows
        if sentence_rows:
            self.sentence_matrix = self.vectorizer.transform(
                [normalize_text(sentence) for _, sentence in sentence_rows]
            )
        else:
            self.sentence_matrix = None

    def search(self, query: str, *, limit: int = 5) -> list[dict[str, Any]]:
        normalized = normalize_text(query)
        if not normalized or self.matrix.shape[0] == 0:
            return []
        from sklearn.metrics.pairwise import cosine_similarity

        query_vector = self.vectorizer.transform([normalized])
        scores = cosine_similarity(query_vector, self.matrix).ravel()
        order = np.argsort(-scores)
        results: list[dict[str, Any]] = []
        for index in order[: max(limit * 2, limit)]:
            chunk = self.chunks[int(index)]
            score = float(scores[int(index)]) + float(chunk.get("priority", 0.0))
            results.append({"chunk": chunk, "score": max(score, 0.0), "raw_score": float(scores[int(index)])})
        results.sort(key=lambda item: item["score"], reverse=True)
        return results[:limit]

    def rank_sentences(self, query: str, *, chunk_ids: Iterable[str] | None = None, limit: int = 6) -> list[dict[str, Any]]:
        if self.sentence_matrix is None:
            return []
        from sklearn.metrics.pairwise import cosine_similarity

        allowed = set(chunk_ids) if chunk_ids is not None else None
        query_vector = self.vectorizer.transform([normalize_text(query)])
        scores = cosine_similarity(query_vector, self.sentence_matrix).ravel()
        ranked = []
        seen: set[str] = set()
        for index in np.argsort(-scores):
            chunk_index, sentence = self.sentence_rows[int(index)]
            chunk = self.chunks[chunk_index]
            if allowed is not None and str(chunk.get("id", "")) not in allowed:
                continue
            key = sentence.casefold()
            if key in seen:
                continue
            seen.add(key)
            ranked.append({
                "sentence": sentence,
                "score": float(scores[int(index)]),
                "chunk": chunk,
            })
            if len(ranked) >= limit:
                break
        return ranked


@lru_cache(maxsize=1)
def default_retrieval_index() -> RetrievalIndex:
    return RetrievalIndex(build_chunks())


__all__ = [
    "RetrievalIndex",
    "build_chunks",
    "build_knowledge_chunks",
    "default_retrieval_index",
    "normalize_text",
]
