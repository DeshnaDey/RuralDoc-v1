"""
scripts/seed_embeddings.py — populate the *_embeddings tables via the
HF-backed Embedder.

Run this AFTER:
  • Migration 002 has been applied (vector(1024) columns + truncated tables)
  • seed_knowledge.py has populated the relational rows (diseases, symptoms,
    tests, facilities, etc.)

What gets seeded
    • disease_embeddings  — one row per disease in the active knowledge_version,
                            embedding = name + prevalence_text + red_flags_text
    • symptom_embeddings  — one row per symptom (active version), embedding = name
    • case_embeddings     — one row per scenario (active version),
                            embedding = narrative composed from
                            hidden_diagnosis, demographics, day-1 symptoms
    • patient_embeddings  — skipped if the patients table is empty (it usually
                            is in dev — patients are created at runtime).

Idempotent: uses INSERT ... ON CONFLICT (id) DO UPDATE so reruns refresh
existing rows. After migration 002 the tables are empty so the first run
inserts everything.

Run from project root:
    python -m scripts.seed_embeddings
    python -m scripts.seed_embeddings --batch-size 16
    python -m scripts.seed_embeddings --skip-cases
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Make `db.*`, `rag.*`, `env.*` importable when run as a script
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import psycopg
from psycopg.rows import dict_row

from db.settings import settings
from rag.embeddings import Embedder
from env.scenarios import scenarios_v2


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("seed_embeddings")


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers — text composition
# ─────────────────────────────────────────────────────────────────────────────


def _disease_text(row: dict) -> str:
    """Compose the embedding text for a disease row."""
    parts = [row["name"]]
    if row.get("prevalence_text"):
        parts.append(row["prevalence_text"])
    if row.get("evolution_text"):
        parts.append(row["evolution_text"])
    if row.get("red_flags_text"):
        parts.append(row["red_flags_text"])
    return " — ".join(p.strip() for p in parts if p)


def _scenario_text(sc: dict) -> str:
    """Compose the embedding text for a scenario row."""
    demo = sc.get("patient_demographics", {})
    age = demo.get("age", "")
    gender = demo.get("gender", "")
    loc = demo.get("location", "")
    day1 = (sc.get("daily_progression") or {}).get(1) or {}
    sym = day1.get("symptoms", [])
    parts = [
        sc.get("hidden_diagnosis", ""),
        f"{age}{gender[0].upper() if gender else ''}".strip(),
        loc,
        ", ".join(sym[:6]),
    ]
    return " — ".join(p for p in (s.strip() if isinstance(s, str) else str(s) for s in parts) if p)


# ─────────────────────────────────────────────────────────────────────────────
#  Seeders — one per table
# ─────────────────────────────────────────────────────────────────────────────


async def seed_disease_embeddings(
    conn: psycopg.AsyncConnection,
    embedder: Embedder,
    batch_size: int = 16,
) -> int:
    """Embed every disease in the active knowledge_version."""
    cur = await conn.execute(
        """
        SELECT d.id, d.name, d.prevalence_text, d.evolution_text, d.red_flags_text
        FROM   public.diseases d
        JOIN   public.knowledge_versions kv
               ON kv.id = d.version_id AND kv.is_active
        ORDER  BY d.id
        """
    )
    rows = await cur.fetchall()
    if not rows:
        log.warning("no diseases in active version — skipping disease_embeddings")
        return 0

    inserted = 0
    for i in range(0, len(rows), batch_size):
        chunk = rows[i:i + batch_size]
        texts = [_disease_text(r) for r in chunk]
        log.info("embedding diseases [%d:%d] of %d", i, i + len(chunk), len(rows))
        vecs = await embedder.embed_batch(texts)
        async with conn.cursor() as cur_w:
            for r, vec, txt in zip(chunk, vecs, texts):
                await cur_w.execute(
                    """
                    INSERT INTO public.disease_embeddings
                        (disease_id, embedding, text_summary)
                    VALUES (%s, %s::vector, %s)
                    ON CONFLICT (disease_id) DO UPDATE
                        SET embedding   = EXCLUDED.embedding,
                            text_summary = EXCLUDED.text_summary,
                            updated_at  = now()
                    """,
                    (r["id"], vec, txt),
                )
                inserted += 1
        await conn.commit()
    log.info("disease_embeddings: inserted/upserted %d rows", inserted)
    return inserted


async def seed_symptom_embeddings(
    conn: psycopg.AsyncConnection,
    embedder: Embedder,
    batch_size: int = 32,
) -> int:
    """Embed every symptom name."""
    cur = await conn.execute(
        """
        SELECT s.id, s.name
        FROM   public.symptoms s
        ORDER  BY s.id
        """
    )
    rows = await cur.fetchall()
    if not rows:
        log.warning("no symptoms in DB — skipping symptom_embeddings")
        return 0

    inserted = 0
    for i in range(0, len(rows), batch_size):
        chunk = rows[i:i + batch_size]
        texts = [r["name"] for r in chunk]
        log.info("embedding symptoms [%d:%d] of %d", i, i + len(chunk), len(rows))
        vecs = await embedder.embed_batch(texts)
        async with conn.cursor() as cur_w:
            for r, vec in zip(chunk, vecs):
                await cur_w.execute(
                    """
                    INSERT INTO public.symptom_embeddings
                        (symptom_id, embedding)
                    VALUES (%s, %s::vector)
                    ON CONFLICT (symptom_id) DO UPDATE
                        SET embedding  = EXCLUDED.embedding,
                            updated_at = now()
                    """,
                    (r["id"], vec),
                )
                inserted += 1
        await conn.commit()
    log.info("symptom_embeddings: inserted/upserted %d rows", inserted)
    return inserted


async def seed_case_embeddings(
    conn: psycopg.AsyncConnection,
    embedder: Embedder,
    batch_size: int = 16,
) -> int:
    """
    Embed every seeded scenario in the active knowledge_version. Pairs each
    scenarios.id (UUID) with the matching scenarios_v2 entry by external_id.
    """
    cur = await conn.execute(
        """
        SELECT sc.id AS scenario_id, sc.external_id
        FROM   public.scenarios sc
        JOIN   public.knowledge_versions kv
               ON kv.id = sc.version_id AND kv.is_active
        ORDER  BY sc.external_id
        """
    )
    rows = await cur.fetchall()
    if not rows:
        log.warning("no scenarios in active version — skipping case_embeddings")
        return 0

    by_extid = {s["id"]: s for s in scenarios_v2}
    pairs: list[tuple[str, dict]] = []
    for r in rows:
        sc = by_extid.get(r["external_id"])
        if sc is not None:
            pairs.append((r["scenario_id"], sc))
        else:
            log.warning("scenario external_id=%s not in scenarios_v2", r["external_id"])

    inserted = 0
    for i in range(0, len(pairs), batch_size):
        chunk = pairs[i:i + batch_size]
        texts = [_scenario_text(sc) for _, sc in chunk]
        log.info("embedding cases [%d:%d] of %d", i, i + len(chunk), len(pairs))
        vecs = await embedder.embed_batch(texts)
        async with conn.cursor() as cur_w:
            for (sid, _), vec, txt in zip(chunk, vecs, texts):
                await cur_w.execute(
                    """
                    INSERT INTO public.case_embeddings
                        (scenario_id, embedding, narrative)
                    VALUES (%s, %s::vector, %s)
                    ON CONFLICT (scenario_id) DO UPDATE
                        SET embedding  = EXCLUDED.embedding,
                            narrative  = EXCLUDED.narrative,
                            updated_at = now()
                    """,
                    (sid, vec, txt),
                )
                inserted += 1
        await conn.commit()
    log.info("case_embeddings: inserted/upserted %d rows", inserted)
    return inserted


# ─────────────────────────────────────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────────────────────────────────────


async def amain(args: argparse.Namespace) -> int:
    embedder = Embedder()
    # Force config resolution up front so we fail fast if HF_TOKEN is missing
    embedder._ensure_config()  # type: ignore[attr-defined]
    log.info("using embedder model=%s mode=%s dim=%d",
             embedder._model, embedder._mode, embedder.dim)

    total = 0
    try:
        async with await psycopg.AsyncConnection.connect(
            settings.supabase_db_url,
            row_factory=dict_row,
            autocommit=False,
        ) as conn:
            if not args.skip_diseases:
                total += await seed_disease_embeddings(
                    conn, embedder, batch_size=args.batch_size
                )
            if not args.skip_symptoms:
                total += await seed_symptom_embeddings(
                    conn, embedder, batch_size=args.batch_size * 2
                )
            if not args.skip_cases:
                total += await seed_case_embeddings(
                    conn, embedder, batch_size=args.batch_size
                )
    finally:
        await embedder.aclose()

    log.info("DONE — %d embedding rows inserted/updated", total)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reseed *_embeddings tables via the HF-backed Embedder."
    )
    parser.add_argument("--batch-size", type=int, default=16,
                        help="Texts per HF API call (default 16).")
    parser.add_argument("--skip-diseases", action="store_true")
    parser.add_argument("--skip-symptoms", action="store_true")
    parser.add_argument("--skip-cases", action="store_true")
    args = parser.parse_args()
    return asyncio.run(amain(args))


if __name__ == "__main__":
    sys.exit(main())
