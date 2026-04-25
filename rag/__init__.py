"""
rag — Retrieval-Augmented Generation layer for RuralDocEnv.

Staging area for the production RAG engine. Everything exported here is a
Protocol or stub so the rest of the code can type-hint / wire against it
without depending on a concrete implementation.

Expected flow once implemented:
    env = MedicalDiagnosisEnvironment(rag_engine=MyRagEngine(...))
    obs = env.reset(scenario=tb)
    result = env.step(action)
    # env.step() calls rag_engine.retrieve() and attaches RAGContext
    # to result.info["rag"]; inference.py renders it into the next prompt.
"""

from rag.engine import RAGEngine, RAGContext, NullRAGEngine
from rag.retriever import Retriever
from rag.embeddings import Embedder

__all__ = [
    "RAGEngine",
    "RAGContext",
    "NullRAGEngine",
    "Retriever",
    "Embedder",
]
