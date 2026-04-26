"""
nlp/vocab.py — SymptomVocab: in-memory symptom cache with pgvector matching.

WHY THIS EXISTS
---------------
The symptoms table is a small (~100–500 rows), near-static reference table.
Loading it into memory at startup means every patient parse costs zero FK
traversals. Novel symptoms discovered by the extractor are added via add(),
which writes to DB and updates the in-memory state atomically.

MATCHING STRATEGY
-----------------
Two-pass, in priority order:

  1. Fuzzy string match (rapidfuzz) against in-memory symptom names.
     Fast, no I/O. Catches exact spellings and close variants.
     Threshold: score >= FUZZY_THRESHOLD (default 80).

  2. pgvector cosine similarity on symptom_embeddings.
     One indexed DB query per unmatched symptom.
     Handles paraphrasing, Hindi-English transliteration, synonyms.
     Only runs if pass 1 finds no match above threshold.

USAGE
-----
    # At server startup (inside lifespan):
    vocab = await SymptomVocab.load(pool, version_id=active_version_id)
    app.state.vocab = vocab

    # During patient parse:
    matches = await vocab.match("bukhaar teen din se", pool)
    # → [SymptomMatch(symptom_id=12, name="fever", score=0.91, novel=False)]

    # After auto_migrate upserts a novel symptom:
    vocab.add({"id": 99, "name": "eye pain", "category": "ophthalmology"}, embedding)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from rapidfuzz import process as fuzz_process, fuzz

log = logging.getLogger("ruraldoc.nlp.vocab")

FUZZY_THRESHOLD = 80       # rapidfuzz WRatio score 0–100
VECTOR_THRESHOLD = 0.75    # cosine similarity 0–1 (1 = identical)
TOP_K_VECTOR = 3           # how many pgvector neighbours to return


@dataclass
class SymptomMatch:
    symptom_id: int
    name: str
    score: float        # 0–1; fuzzy scores are normalised from 0–100
    novel: bool = False # True when this symptom was auto-upserted this session


@dataclass
class SymptomVocab:
    """
    In-memory symptom vocabulary.

    Attributes:
        symptoms    list of dicts: {id, name, category, version_id}
        _name_index dict mapping lowercase name → symptom dict (fast lookup)
        version_id  knowledge version these symptoms belong to
    """

    symptoms: list[dict] = field(default_factory=list)
    _name_index: dict[str, dict] = field(default_factory=dict, repr=False)
    version_id: int | None = None

    # ── Construction ──────────────────────────────────────────────────────

    @classmethod
    async def load(cls, pool, version_id: int) -> "SymptomVocab":
        """
        Load all symptoms for the given knowledge version from Supabase.
        Call once at server startup; store result in app.state.vocab.
        """
        t0 = time.monotonic()
        async with pool.connection() as conn:
            rows = await conn.execute(
                """
                SELECT id, name, category, version_id
                FROM public.symptoms
                WHERE version_id = %s
                ORDER BY name
                """,
                (version_id,),
            )
            symptoms = [
                {"id": r[0], "name": r[1], "category": r[2], "version_id": r[3]}
                for r in await rows.fetchall()
            ]

        vocab = cls(symptoms=symptoms, version_id=version_id)
        vocab._rebuild_index()

        elapsed = (time.monotonic() - t0) * 1000
        log.info(
            "SymptomVocab loaded: %d symptoms (version_id=%s) in %.1f ms",
            len(symptoms), version_id, elapsed,
        )
        return vocab

    def _rebuild_index(self) -> None:
        self._name_index = {s["name"].lower(): s for s in self.symptoms}

    # ── Matching ──────────────────────────────────────────────────────────

    async def match(
        self,
        query: str,
        pool,
        query_embedding: list[float] | None = None,
    ) -> list[SymptomMatch]:
        """
        Match a single extracted symptom string against the vocab.

        Args:
            query           The extracted symptom text (e.g. "bukhaar")
            pool            psycopg async pool (used only for vector fallback)
            query_embedding Pre-computed embedding for query; if None and
                            vector fallback is needed, caller should embed first.

        Returns:
            List of SymptomMatch, best match first. Empty if nothing found
            above thresholds.
        """
        query_lower = query.lower().strip()

        # ── Pass 1: fuzzy string match (no I/O) ──────────────────────────
        names = list(self._name_index.keys())
        if names:
            result = fuzz_process.extractOne(
                query_lower, names,
                scorer=fuzz.WRatio,
                score_cutoff=FUZZY_THRESHOLD,
            )
            if result:
                matched_name, score, _ = result
                symptom = self._name_index[matched_name]
                return [SymptomMatch(
                    symptom_id=symptom["id"],
                    name=symptom["name"],
                    score=round(score / 100, 3),
                    novel=False,
                )]

        # ── Pass 2: pgvector cosine similarity (one indexed query) ────────
        if query_embedding is None:
            # Caller didn't pre-embed — signal that embedding is needed.
            # auto_migrate.py handles this path.
            log.debug("vocab.match: no fuzzy hit for %r and no embedding provided", query)
            return []

        async with pool.connection() as conn:
            rows = await conn.execute(
                """
                SELECT s.id, s.name, s.category,
                       1 - (se.embedding <=> %s::vector) AS similarity
                FROM public.symptom_embeddings se
                JOIN public.symptoms s ON s.id = se.symptom_id
                WHERE s.version_id = %s
                  AND 1 - (se.embedding <=> %s::vector) >= %s
                ORDER BY se.embedding <=> %s::vector
                LIMIT %s
                """,
                (
                    query_embedding,
                    self.version_id,
                    query_embedding,
                    VECTOR_THRESHOLD,
                    query_embedding,
                    TOP_K_VECTOR,
                ),
            )
            hits = await rows.fetchall()

        return [
            SymptomMatch(
                symptom_id=row[0],
                name=row[1],
                score=round(float(row[3]), 3),
                novel=False,
            )
            for row in hits
        ]

    # ── Cache update ──────────────────────────────────────────────────────

    def add(self, symptom: dict, embedding: list[float] | None = None) -> None:
        """
        Add a newly upserted symptom to the in-memory cache.
        Call this immediately after auto_migrate writes the DB row so
        subsequent patients in the same server session benefit from it.

        Args:
            symptom   dict with keys: id, name, category, version_id
            embedding The embedding vector (stored in symptom_embeddings);
                      not held in memory here — pgvector handles it.
        """
        self.symptoms.append(symptom)
        self._name_index[symptom["name"].lower()] = symptom
        log.info("SymptomVocab.add: cached novel symptom %r (id=%s)", symptom["name"], symptom["id"])

    # ── Introspection ─────────────────────────────────────────────────────

    def __len__(self) -> int:
        return len(self.symptoms)

    def __repr__(self) -> str:
        return f"SymptomVocab(n={len(self)}, version_id={self.version_id})"
