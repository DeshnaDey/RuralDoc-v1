"""
rag/embeddings.py — Stub for the embedding layer.

Two jobs live here:
  1. `embed(text)` / `embed_batch(texts)` — text → vector (OpenAI, local,
     etc.). Used at query time and when (re)building the *_embeddings
     tables.
  2. Regeneration: when Layer 1/2/3 rows change, the embeddings tables
     should be refreshed. That scheduler / cron lives here too.

The migration created these embedding tables (1536-dim by default; swap to
whatever model you pick):
    disease_embeddings, symptom_embeddings, patient_embeddings,
    case_embeddings

When the real Embedder goes in, it should expose:
    await embed(text) -> list[float]          # 1536-dim
    await embed_batch(texts) -> list[list[float]]
"""

from __future__ import annotations


class Embedder:
    """
    Placeholder embedder. Real implementation will live alongside this class
    (or as a subclass — e.g. OpenAIEmbedder).
    """

    dim: int = 1536

    async def embed(self, text: str) -> list[float]:
        raise NotImplementedError("embed is not implemented yet")

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError("embed_batch is not implemented yet")
