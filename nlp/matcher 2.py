"""
nlp/matcher.py — Match a ParsedComplaint against the SymptomVocab.

For each ExtractedSymptom:
  1. Try fuzzy string match (no I/O, in-memory)
  2. If no fuzzy hit → embed the symptom name, try pgvector cosine match
  3. If still no match → mark as novel (auto_migrate will handle it)

Returns a MatchResult containing matched SymptomMatches and a list of
unmatched ExtractedSymptoms that need auto-migration.

USAGE
-----
    result = await match_complaint(parsed, vocab, pool, embedder)
    # result.matched  → [SymptomMatch(...), ...]
    # result.novel    → [ExtractedSymptom(...), ...]  ← needs auto_migrate
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

from nlp.extractor import ExtractedSymptom, ParsedComplaint
from nlp.vocab import SymptomMatch, SymptomVocab
from rag.embeddings import Embedder

log = logging.getLogger("ruraldoc.nlp.matcher")


@dataclass
class MatchResult:
    """
    Output of match_complaint().

    matched:    Symptoms successfully resolved to a symptoms table row.
    novel:      Extracted symptoms with no DB match — candidates for
                auto_migrate.upsert_novel().
    embeddings: query embeddings keyed by extracted symptom name,
                so auto_migrate can reuse them without re-embedding.
    """
    matched: list[SymptomMatch] = field(default_factory=list)
    novel: list[ExtractedSymptom] = field(default_factory=list)
    embeddings: dict[str, list[float]] = field(default_factory=dict)


async def match_complaint(
    parsed: ParsedComplaint,
    vocab: SymptomVocab,
    pool,
    embedder: Embedder,
) -> MatchResult:
    """
    Match all symptoms in a ParsedComplaint against the SymptomVocab.

    Embedding calls are batched for symptoms that need the vector fallback,
    so at most one embed_batch call per patient (not one per symptom).

    Args:
        parsed      Output of SymptomExtractor.extract()
        vocab       Loaded SymptomVocab from app.state.vocab
        pool        psycopg async pool (for pgvector queries)
        embedder    Embedder instance (for computing query vectors)

    Returns:
        MatchResult with .matched, .novel, .embeddings
    """
    result = MatchResult()

    if not parsed.symptoms:
        return result

    # ── Pass 1: fuzzy match (no I/O) ─────────────────────────────────────
    needs_vector: list[ExtractedSymptom] = []
    for sym in parsed.symptoms:
        hits = await vocab.match(sym.name, pool, query_embedding=None)
        if hits:
            result.matched.append(hits[0])
            log.debug("fuzzy match: %r → %r (%.2f)", sym.name, hits[0].name, hits[0].score)
        else:
            needs_vector.append(sym)

    if not needs_vector:
        return result

    # ── Pass 2: embed unmatched symptoms in one batch call ────────────────
    names_to_embed = [s.name for s in needs_vector]
    try:
        vecs = await embedder.embed_batch(names_to_embed)
    except Exception as exc:
        log.warning("embed_batch failed: %s — marking all as novel", exc)
        result.novel.extend(needs_vector)
        return result

    # Store embeddings for reuse by auto_migrate
    for sym, vec in zip(needs_vector, vecs):
        result.embeddings[sym.name] = vec

    # ── Pass 2b: pgvector cosine match for each unmatched symptom ─────────
    for sym, vec in zip(needs_vector, vecs):
        hits = await vocab.match(sym.name, pool, query_embedding=vec)
        if hits:
            result.matched.append(hits[0])
            log.debug("vector match: %r → %r (%.3f)", sym.name, hits[0].name, hits[0].score)
        else:
            log.info("novel symptom detected: %r (no fuzzy or vector hit)", sym.name)
            result.novel.append(sym)

    return result
