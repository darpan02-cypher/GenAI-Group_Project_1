"""Retrieval and context-window expansion."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .index import KnowledgeIndex

SIMILARITY_THRESHOLD = 0.30


def retrieve_context(
    index: KnowledgeIndex,
    query: str,
    top_k: int = 3,
    window: int = 1,
    threshold: float = SIMILARITY_THRESHOLD,
) -> tuple[str, list[str]] | None:
    hits = index.search(query, limit=top_k)
    if not hits or hits[0][1] < threshold:
        return None

    documents: dict[str, str] = {}
    for chunk, _score in hits:
        documents.setdefault(chunk.doc_id, index.expand(chunk, window=window))
    sources = [f"{doc_id}.md" for doc_id in documents]
    context = "\n\n---\n\n".join(
        f"[{doc_id}]\n{text}" for doc_id, text in documents.items()
    )
    return context, sources