"""
rag — Retrieval-Augmented Generation layer for RuralDocEnv.

Production flow:
    from rag import PgRAGEngine
    from rag.embeddings import Embedder
    from db.pool import get_pool

    pool   = await get_pool()
    engine = PgRAGEngine(pool=pool, embedder=Embedder())
    ctx    = await engine.retrieve("fever night sweats weight loss Delhi 34M", k=3)
    # ctx.snippets → list of formatted clinical guideline strings
"""

from rag.engine import RAGEngine, RAGContext, NullRAGEngine
from rag.retriever import Retriever
from rag.embeddings import Embedder
from rag.engine_pg import PgRAGEngine

__all__ = [
    "RAGEngine",
    "RAGContext",
    "NullRAGEngine",
    "Retriever",
    "Embedder",
    "PgRAGEngine",
]
