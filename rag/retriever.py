"""
rag/retriever.py — Vector + graph retrieval helpers backed by psycopg3 + pgvector.

Two-phase retrieval:

  Phase 1 — vector_search(embedding, k)
    Cosine similarity search over disease_embeddings (pgvector).
    Filters to the active knowledge version automatically.
    Returns a ranked list of VectorHit, best first.

  Phase 2 — graph_expand(hits, depth=1)
    For each disease hit, pull associated relational context via FK joins:
      disease_symptoms    — typicality-ranked presenting symptoms
      disease_tests       — info_gain-ranked diagnostic tests
      disease_red_flags   — referral-forcing flags first
      disease_referrals   — facility + trigger criteria
      disease_differentials — top mimics with distinguishing feature
    All five queries share one connection; results are grouped and merged
    into an enriched dict per hit.

  hybrid_retrieve(query_vec, k, *, filters, graph_depth=1)
    Convenience wrapper: vector_search → graph_expand in one call.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

log = logging.getLogger("ruraldoc.rag.retriever")


@dataclass
class VectorHit:
    """One row back from a pgvector similarity query."""

    table: str
    row_id: int | str
    distance: float
    payload: dict[str, Any]


class Retriever:
    """Vector + graph retriever. Pass a psycopg3 AsyncConnectionPool at construction."""

    def __init__(self, pool) -> None:
        self.pool = pool

    async def vector_search(
        self,
        embedding: list[float],
        *,
        k: int = 5,
        filters: dict | None = None,
        similarity_threshold: float = 0.45,
    ) -> list[VectorHit]:
        if filters and "version_id" in filters:
            version_join  = ""
            version_where = "AND d.version_id = %s"
            version_param = [filters["version_id"]]
        else:
            version_join  = "JOIN public.knowledge_versions kv ON kv.id = d.version_id AND kv.is_active"
            version_where = ""
            version_param = []

        name_where = ""
        name_param: list[Any] = []
        if filters and "disease_name" in filters:
            name_where = "AND d.name ILIKE %s"
            name_param = [f"%{filters['disease_name']}%"]

        sql = f"""
            SELECT d.id, d.name, d.prevalence_text, d.evolution_text,
                   d.red_flags_text, d.icd10,
                   1 - (de.embedding <=> %s::vector) AS similarity
            FROM public.disease_embeddings de
            JOIN public.diseases d ON d.id = de.disease_id
            {version_join}
            WHERE 1 - (de.embedding <=> %s::vector) >= %s
            {version_where}
            {name_where}
            ORDER BY de.embedding <=> %s::vector
            LIMIT %s;
        """
        params = ([embedding, embedding, similarity_threshold]
                  + version_param + name_param + [embedding, k])

        try:
            async with self.pool.connection() as conn:
                cur = await conn.execute(sql, params)
                rows = await cur.fetchall()
        except Exception as exc:
            log.warning("vector_search failed: %s", exc)
            return []

        return [
            VectorHit(
                table="disease_embeddings",
                row_id=int(row[0]),
                distance=round(1.0 - float(row[6]), 4),
                payload={
                    "disease_id":      int(row[0]),
                    "name":            row[1],
                    "prevalence_text": row[2],
                    "evolution_text":  row[3],
                    "red_flags_text":  row[4],
                    "icd10":           row[5],
                    "similarity":      round(float(row[6]), 4),
                },
            )
            for row in rows
        ]

    async def graph_expand(
        self,
        hits: list[VectorHit],
        *,
        depth: int = 1,
    ) -> list[dict[str, Any]]:
        if not hits:
            return []

        disease_ids = [h.row_id for h in hits]
        ph = ",".join(["%s"] * len(disease_ids))

        try:
            async with self.pool.connection() as conn:
                cur = await conn.execute(
                    f"SELECT ds.disease_id, s.name, ds.phase, ds.typicality "
                    f"FROM public.disease_symptoms ds "
                    f"JOIN public.symptoms s ON s.id = ds.symptom_id "
                    f"WHERE ds.disease_id IN ({ph}) "
                    f"ORDER BY ds.disease_id, ds.typicality DESC NULLS LAST;",
                    disease_ids,
                )
                symptom_rows = await cur.fetchall()

                cur = await conn.execute(
                    f"SELECT dt.disease_id, t.name, dt.role, dt.info_gain "
                    f"FROM public.disease_tests dt "
                    f"JOIN public.tests t ON t.id = dt.test_id "
                    f"WHERE dt.disease_id IN ({ph}) "
                    f"ORDER BY dt.disease_id, dt.info_gain DESC NULLS LAST;",
                    disease_ids,
                )
                test_rows = await cur.fetchall()

                cur = await conn.execute(
                    f"SELECT disease_id, red_flag_text, forces_referral "
                    f"FROM public.disease_red_flags "
                    f"WHERE disease_id IN ({ph}) "
                    f"ORDER BY disease_id, forces_referral DESC NULLS LAST;",
                    disease_ids,
                )
                red_flag_rows = await cur.fetchall()

                cur = await conn.execute(
                    f"SELECT dr.disease_id, f.name, f.tier, dr.exact_signs, dr.do_not_wait_reason "
                    f"FROM public.disease_referrals dr "
                    f"JOIN public.facilities f ON f.id = dr.facility_id "
                    f"WHERE dr.disease_id IN ({ph}) ORDER BY dr.disease_id;",
                    disease_ids,
                )
                referral_rows = await cur.fetchall()

                cur = await conn.execute(
                    f"SELECT dd.disease_id, d.name, dd.distinguishing_feature "
                    f"FROM public.disease_differentials dd "
                    f"JOIN public.diseases d ON d.id = dd.mimic_disease_id "
                    f"WHERE dd.disease_id IN ({ph}) ORDER BY dd.disease_id;",
                    disease_ids,
                )
                differential_rows = await cur.fetchall()

        except Exception as exc:
            log.warning("graph_expand failed: %s", exc)
            return [
                {**h.payload, "symptoms": [], "tests": [], "red_flags": [], "referrals": [], "differentials": []}
                for h in hits
            ]

        syms:   dict[int, list[dict]] = defaultdict(list)
        tests:  dict[int, list[dict]] = defaultdict(list)
        rflags: dict[int, list[dict]] = defaultdict(list)
        refs:   dict[int, list[dict]] = defaultdict(list)
        diffs:  dict[int, list[dict]] = defaultdict(list)

        for r in symptom_rows:
            syms[int(r[0])].append({"name": r[1], "phase": r[2], "typicality": r[3]})
        for r in test_rows:
            tests[int(r[0])].append({"name": r[1], "role": r[2], "info_gain": r[3]})
        for r in red_flag_rows:
            rflags[int(r[0])].append({"text": r[1], "forces_referral": r[2]})
        for r in referral_rows:
            refs[int(r[0])].append({"facility": r[1], "tier": r[2], "exact_signs": r[3], "do_not_wait_reason": r[4]})
        for r in differential_rows:
            diffs[int(r[0])].append({"mimic": r[1], "distinguishing": r[2]})

        return [
            {
                **h.payload,
                "symptoms":      syms.get(int(h.row_id), []),
                "tests":         tests.get(int(h.row_id), []),
                "red_flags":     rflags.get(int(h.row_id), []),
                "referrals":     refs.get(int(h.row_id), []),
                "differentials": diffs.get(int(h.row_id), []),
            }
            for h in hits
        ]

    async def hybrid_retrieve(
        self,
        query_vec: list[float],
        k: int = 5,
        *,
        filters: dict | None = None,
        graph_depth: int = 1,
    ) -> list[dict[str, Any]]:
        hits = await self.vector_search(query_vec, k=k, filters=filters)
        if not hits:
            return []
        return await self.graph_expand(hits, depth=graph_depth)
