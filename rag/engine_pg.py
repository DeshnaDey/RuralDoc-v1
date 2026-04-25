"""
rag/engine_pg.py — Pgvector-backed RAGEngine (concrete implementation).

Pipeline on each retrieve(query) call:
  1. Embed query via Embedder (OpenAI-compatible).
  2. vector_search disease_embeddings for top-k diseases.
  3. graph_expand each hit (symptoms, tests, red flags, referrals, differentials).
  4. Format into compact LLM-readable snippets.
  5. Return RAGContext.

Never raises — every failure returns an empty RAGContext.
"""

from __future__ import annotations

import logging
from typing import Any

from rag.engine import RAGContext
from rag.embeddings import Embedder
from rag.retriever import Retriever

log = logging.getLogger("ruraldoc.rag.engine_pg")


class PgRAGEngine:
    """
    pgvector-backed RAGEngine. Coroutine-safe.

    Args:
        pool      psycopg3 AsyncConnectionPool (from db.pool.get_pool()).
        embedder  Embedder instance; created lazily if None.
        k         Default number of disease hits per retrieve() call.
    """

    def __init__(self, pool, embedder: Embedder | None = None, k: int = 3) -> None:
        self._retriever = Retriever(pool)
        self._embedder  = embedder or Embedder()
        self._default_k = k

    async def retrieve(
        self,
        query: str,
        *,
        k: int | None = None,
        filters: dict | None = None,
    ) -> RAGContext:
        k = k if k is not None else self._default_k

        if not query or not query.strip():
            return RAGContext(query=query, meta={"engine": "pg", "k": k, "hits": 0})

        try:
            embedding = await self._embedder.embed(query)
        except Exception as exc:
            log.warning("PgRAGEngine: embed failed (%s)", exc)
            return RAGContext(query=query, meta={"engine": "pg", "error": f"embed: {exc}"})

        try:
            hits = await self._retriever.vector_search(embedding, k=k, filters=filters)
        except Exception as exc:
            log.warning("PgRAGEngine: vector_search failed (%s)", exc)
            return RAGContext(query=query, meta={"engine": "pg", "error": f"vector_search: {exc}"})

        if not hits:
            return RAGContext(query=query, meta={"engine": "pg", "k": k, "hits": 0})

        try:
            enriched = await self._retriever.graph_expand(hits)
        except Exception as exc:
            log.warning("PgRAGEngine: graph_expand failed (%s) — vector only", exc)
            enriched = [
                {**h.payload, "symptoms": [], "tests": [], "red_flags": [], "referrals": [], "differentials": []}
                for h in hits
            ]

        snippets = [_format_snippet(d) for d in enriched]
        sources  = [{"disease": d.get("name", ""), "similarity": d.get("similarity", 0.0), "icd10": d.get("icd10")} for d in enriched]

        return RAGContext(
            query=query,
            snippets=snippets,
            sources=sources,
            meta={"engine": "pg", "k": k, "hits": len(hits)},
        )


def _format_snippet(disease: dict[str, Any]) -> str:
    """
    Format one enriched disease dict into a compact clinical guideline string.

    Example:
        [DISEASE: Tuberculosis (ICD10: A15)]
        Context: Highly prevalent in urban slums.
        Red flags: REFER IMMEDIATELY if: haemoptysis
        Typical symptoms: cough (typical), night sweats (typical)
        Key tests: sputum_smear [conclusive, info_gain=1.0]
        Refer to: DOTS centre (district) — signs: AFB+; do not wait: haemoptysis
        Differentials: distinguish from kala_azar (splenomegaly absent)
    """
    lines: list[str] = []

    name  = disease.get("name", "Unknown")
    icd10 = disease.get("icd10") or ""

    header = f"[DISEASE: {name.title()}"
    if icd10:
        header += f" (ICD10: {icd10})"
    lines.append(header + "]")

    if prev := disease.get("prevalence_text"):
        lines.append(f"Context: {prev.strip()}")

    red_flags: list[dict] = disease.get("red_flags", [])
    if not red_flags and (rf_text := disease.get("red_flags_text")):
        lines.append(f"Red flags: {rf_text.strip()}")
    elif red_flags:
        forcing     = [rf["text"] for rf in red_flags if rf.get("forces_referral")]
        non_forcing = [rf["text"] for rf in red_flags if not rf.get("forces_referral")]
        parts: list[str] = []
        if forcing:
            parts.append(f"REFER IMMEDIATELY if: {'; '.join(forcing)}")
        if non_forcing:
            parts.append(f"watch for: {'; '.join(non_forcing)}")
        if parts:
            lines.append("Red flags: " + " | ".join(parts))

    symptoms: list[dict] = disease.get("symptoms", [])
    if symptoms:
        sym_parts = []
        for s in symptoms[:6]:
            label = s["name"]
            t = s.get("typicality")
            if t is not None:
                t = float(t)
                q = "typical" if t >= 0.7 else "moderate" if t >= 0.4 else "atypical"
                label += f" ({q})"
            sym_parts.append(label)
        lines.append(f"Typical symptoms: {', '.join(sym_parts)}")

    tests: list[dict] = disease.get("tests", [])
    if tests:
        test_parts = []
        for t in tests[:5]:
            label = t["name"]
            extras = []
            if t.get("role"):
                extras.append(t["role"])
            if t.get("info_gain") is not None:
                extras.append(f"info_gain={float(t['info_gain']):.1f}")
            if extras:
                label += f" [{', '.join(extras)}]"
            test_parts.append(label)
        lines.append(f"Key tests: {', '.join(test_parts)}")

    referrals: list[dict] = disease.get("referrals", [])
    if referrals:
        ref_parts = []
        for r in referrals[:2]:
            part = f"{r['facility']} ({r['tier']})"
            if r.get("exact_signs"):
                part += f" — signs: {r['exact_signs']}"
            if r.get("do_not_wait_reason"):
                part += f"; do not wait: {r['do_not_wait_reason']}"
            ref_parts.append(part)
        lines.append(f"Refer to: {' | '.join(ref_parts)}")

    diffs: list[dict] = disease.get("differentials", [])
    if diffs:
        diff_parts = []
        for d in diffs[:3]:
            part = d["mimic"]
            if d.get("distinguishing"):
                part += f" ({d['distinguishing']})"
            diff_parts.append(part)
        lines.append(f"Differentials: distinguish from {', '.join(diff_parts)}")

    return "\n".join(lines)
