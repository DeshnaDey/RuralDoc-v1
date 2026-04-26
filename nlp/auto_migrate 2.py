"""
nlp/auto_migrate.py — Runtime vocab expansion and patient event writing.

Two responsibilities:

1. upsert_novel(novel_symptoms, embeddings, vocab, pool, version_id)
   For each symptom the matcher couldn't resolve:
     - INSERT into symptoms (upsert on conflict)
     - INSERT into symptom_embeddings
     - Call vocab.add() to update the in-memory cache
     - Returns list[SymptomMatch] so they flow into the same matched list

2. write_patient_events(patient_id, matched, parsed, pool)
   After matching is complete, write one patient_history_events row per
   matched symptom, plus one symptom_extraction_log audit row for the
   full parse result.

DESIGN NOTE — "auto" vs "reviewed" expansion
---------------------------------------------
Novel symptoms are upserted immediately into the symptoms table (Option A).
If you later want Option B (queue for review), replace the INSERT in
upsert_novel with an INSERT into a pending_symptoms table and remove the
vocab.add() call. The rest of the pipeline stays the same.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass

from nlp.extractor import ExtractedSymptom, ParsedComplaint
from nlp.vocab import SymptomMatch, SymptomVocab

log = logging.getLogger("ruraldoc.nlp.auto_migrate")


async def upsert_novel(
    novel: list[ExtractedSymptom],
    embeddings: dict[str, list[float]],
    vocab: SymptomVocab,
    pool,
    version_id: int,
) -> list[SymptomMatch]:
    """
    Upsert novel symptoms to the DB, update vocab cache, return SymptomMatches.

    Args:
        novel       ExtractedSymptoms that matched nothing in the vocab
        embeddings  Pre-computed embedding vectors keyed by symptom name
                    (from matcher.MatchResult.embeddings)
        vocab       Live SymptomVocab (will be mutated via vocab.add())
        pool        psycopg async pool
        version_id  Active knowledge version ID

    Returns:
        list[SymptomMatch] for each upserted symptom (novel=True)
    """
    results: list[SymptomMatch] = []
    if not novel:
        return results

    async with pool.connection() as conn:
        for sym in novel:
            try:
                # Upsert symptom row
                row = await conn.execute(
                    """
                    INSERT INTO public.symptoms (version_id, name, category)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (version_id, name) DO UPDATE
                      SET category = EXCLUDED.category
                    RETURNING id, name, category, version_id
                    """,
                    (version_id, sym.name.lower(), _infer_category(sym.name)),
                )
                symptom_row = await row.fetchone()
                symptom_id, name, category, vid = symptom_row

                # Upsert embedding if we have one
                vec = embeddings.get(sym.name)
                if vec:
                    await conn.execute(
                        """
                        INSERT INTO public.symptom_embeddings (symptom_id, embedding)
                        VALUES (%s, %s::vector)
                        ON CONFLICT (symptom_id) DO UPDATE
                          SET embedding = EXCLUDED.embedding,
                              updated_at = now()
                        """,
                        (symptom_id, vec),
                    )

                # Update in-memory vocab cache immediately
                vocab.add(
                    {"id": symptom_id, "name": name, "category": category, "version_id": vid},
                    embedding=vec,
                )

                results.append(SymptomMatch(
                    symptom_id=symptom_id,
                    name=name,
                    score=1.0,  # it IS this symptom — we just created it
                    novel=True,
                ))
                log.info("auto_migrate: upserted novel symptom %r (id=%s)", name, symptom_id)

            except Exception as exc:
                log.warning("auto_migrate: failed to upsert %r: %s", sym.name, exc)

    return results


async def write_patient_events(
    patient_id: str,
    all_matches: list[SymptomMatch],
    parsed: ParsedComplaint,
    pool,
) -> None:
    """
    Write structured symptom data to the DB for a patient:

      - One patient_history_events row per matched symptom
        (event_type = "symptom_onset", payload has duration/severity)
      - One symptom_extraction_log row for the full parse audit

    Args:
        patient_id  UUID of the patients row (may be None if not yet committed)
        all_matches Merged matched + novel SymptomMatches
        parsed      Full ParsedComplaint from the extractor
        pool        psycopg async pool
    """
    async with pool.connection() as conn:
        # Write one history event per matched symptom
        for match in all_matches:
            try:
                await conn.execute(
                    """
                    INSERT INTO public.patient_history_events
                      (patient_id, event_type, symptom_id, event_at, payload)
                    VALUES (%s, 'symptom_onset', %s, now(), %s)
                    """,
                    (
                        patient_id,
                        match.symptom_id,
                        json.dumps({
                            "source": "nlp_extraction",
                            "novel": match.novel,
                            "score": match.score,
                        }),
                    ),
                )
            except Exception as exc:
                log.warning(
                    "write_patient_events: history event failed for symptom %s: %s",
                    match.symptom_id, exc,
                )

        # Write audit log row
        try:
            matched_json = [
                {
                    "symptom_id": m.symptom_id,
                    "name": m.name,
                    "score": m.score,
                    "novel": m.novel,
                }
                for m in all_matches
            ]
            extracted_json = [s.model_dump() for s in parsed.symptoms]

            await conn.execute(
                """
                INSERT INTO public.symptom_extraction_log
                  (patient_id, raw_text, extracted, matched, urgency_flags,
                   model_used, parse_ms)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    patient_id,
                    parsed.raw_text,
                    json.dumps(extracted_json),
                    json.dumps(matched_json),
                    json.dumps(parsed.urgency_flags),
                    parsed.model_used,
                    parsed.parse_ms,
                ),
            )
        except Exception as exc:
            log.warning("write_patient_events: extraction log failed: %s", exc)


# ── Helpers ───────────────────────────────────────────────────────────────────

_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "respiratory": ["cough", "breath", "wheez", "sputum", "chest", "lungs", "respiratory", "sans"],
    "fever": ["fever", "temperature", "bukhaar", "pyrexia"],
    "gastrointestinal": ["vomit", "nausea", "diarrhea", "diarrhoea", "loose", "stool", "abdomen",
                         "stomach", "pet", "dast", "ulti"],
    "neurological": ["headache", "dizzy", "seizure", "unconscious", "sar", "sardard"],
    "musculoskeletal": ["pain", "ache", "joint", "body", "muscle", "limb", "back", "dard"],
    "ophthalmological": ["eye", "vision", "blur", "aankh"],
    "skin": ["rash", "itch", "swelling", "jaundice", "bleed", "wound"],
    "general": ["fatigue", "weakness", "weight", "appetite", "thakaan", "kamzori"],
}


def _infer_category(symptom_name: str) -> str:
    """
    Heuristic category assignment for novel symptoms based on keyword match.
    Falls back to 'general' if nothing matches.
    """
    lower = symptom_name.lower()
    for category, keywords in _CATEGORY_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return category
    return "general"
