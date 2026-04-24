"""
rag/engine.py — Protocol + null-object for the RAG engine.

The environment calls `engine.retrieve(query)` on every step and attaches
the returned RAGContext to `StepResult.info["rag"]`. That's the entire
contract: one method, one return type.

Production implementations will live alongside this file (e.g. engine_pg.py
for a pgvector-backed engine). Each must subclass `RAGEngine` or duck-type
the same interface.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class RAGContext:
    """
    A single retrieval result handed back to the agent.

    Fields are intentionally loose — the shape will solidify once the real
    engine is built. Keep `sources` as JSON-serialisable dicts so the env
    can embed them in `StepResult.info` without further work.
    """

    query: str
    snippets: list[str] = field(default_factory=list)
    sources: list[dict[str, Any]] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "snippets": self.snippets,
            "sources": self.sources,
            "meta": self.meta,
        }


@runtime_checkable
class RAGEngine(Protocol):
    """
    The only method the environment needs. Implementations can expose more.

    Implementations are expected to be async so they can hit pgvector /
    remote vector stores without blocking the event loop. The env wraps
    retrieve() calls in a try/except so a slow or broken engine never
    crashes a rollout.
    """

    async def retrieve(self, query: str, *, k: int = 5, filters: dict | None = None) -> RAGContext:
        ...


class NullRAGEngine:
    """
    Default engine — does nothing, returns an empty context. Use this when
    you want the env to run without any RAG plumbing (e.g. pure behavioural
    training, or tests).
    """

    async def retrieve(self, query: str, *, k: int = 5, filters: dict | None = None) -> RAGContext:
        return RAGContext(query=query, snippets=[], sources=[], meta={"engine": "null"})
