"""
rag/retriever.py — Stub for vector + graph retrieval helpers.

Layout for the real implementation:

    async def vector_search(embedding, k, filters) -> list[VectorHit]:
        SELECT ... FROM <embedding_table>
        ORDER BY embedding <=> %s
        LIMIT %s;

    async def graph_expand(hits, depth) -> list[dict]:
        # walk disease_red_flags / disease_tests / disease_differentials to
        # pull related rows for each hit.

    async def hybrid_retrieve(query_vec, k, *, filters, graph_depth=1):
        hits = await vector_search(query_vec, k, filters)
        return await graph_expand(hits, graph_depth)

Drop these in when you're ready — the engine in engine.py will call this.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class VectorHit:
    """One row back from a pgvector similarity query."""

    table: str                  # e.g. "disease_embeddings"
    row_id: int | str
    distance: float
    payload: dict[str, Any]     # dict of the joined row, JSON-safe


class Retriever:
    """
    Placeholder retriever. The environment never instantiates this directly
    — it's here so the engine implementation has a place to live.
    """

    async def vector_search(
        self,
        embedding: list[float],
        *,
        k: int = 5,
        filters: dict | None = None,
    ) -> list[VectorHit]:
        raise NotImplementedError("vector_search is not implemented yet")

    async def graph_expand(
        self,
        hits: list[VectorHit],
        *,
        depth: int = 1,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError("graph_expand is not implemented yet")
