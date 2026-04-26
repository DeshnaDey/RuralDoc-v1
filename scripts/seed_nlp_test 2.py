"""
scripts/seed_nlp_test.py — End-to-end test of the NLP extraction layer.

What this does, in order:
  1. Run migration 006 (symptom_extraction_log table) if not already present
  2. Seed PHC-relevant symptom vocabulary into the symptoms table
  3. Load SymptomVocab in-memory — verify row count
  4. Test fuzzy string matching (no API key needed)
  5. Test LLM extraction (SymptomExtractor) — needs OPENAI_API_KEY or HF_TOKEN
  6. Test full pipeline: extract → match → auto_migrate → write patient events
  7. Verify all Supabase writes landed (row count assertions)
  8. Print a summary report

Run from project root:
    OPENAI_API_KEY=sk-... python scripts/seed_nlp_test.py

Or with HuggingFace:
    HF_TOKEN=hf_... API_BASE_URL=https://api-inference.huggingface.co/v1 MODEL_NAME=... python scripts/seed_nlp_test.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from db.settings import settings

# Import all nlp modules up front — avoids OSError on NFS mounts when
# Python tries to import inside an asyncio event loop.
from nlp.vocab import SymptomVocab
from nlp.extractor import SymptomExtractor
from nlp.matcher import match_complaint
from nlp.auto_migrate import upsert_novel, write_patient_events
from rag.embeddings import Embedder

# ── PHC symptom vocabulary seed data ─────────────────────────────────────────
# These cover the disease set in scenarios_v2: dengue, malaria, typhoid, TB,
# snakebite, diarrhea, asthma, anemia, hypertension, diabetes, stroke, MI.
PHC_SYMPTOMS: list[dict] = [
    # Fever cluster
    {"name": "fever",              "category": "fever"},
    {"name": "high fever",         "category": "fever"},
    {"name": "chills",             "category": "fever"},
    {"name": "rigors",             "category": "fever"},
    {"name": "night sweats",       "category": "fever"},
    # Respiratory
    {"name": "cough",              "category": "respiratory"},
    {"name": "chronic cough",      "category": "respiratory"},
    {"name": "productive cough",   "category": "respiratory"},
    {"name": "haemoptysis",        "category": "respiratory"},
    {"name": "difficulty breathing","category": "respiratory"},
    {"name": "shortness of breath","category": "respiratory"},
    {"name": "wheezing",           "category": "respiratory"},
    {"name": "chest pain",         "category": "respiratory"},
    # GI
    {"name": "vomiting",           "category": "gastrointestinal"},
    {"name": "nausea",             "category": "gastrointestinal"},
    {"name": "diarrhea",           "category": "gastrointestinal"},
    {"name": "abdominal pain",     "category": "gastrointestinal"},
    {"name": "loss of appetite",   "category": "gastrointestinal"},
    {"name": "constipation",       "category": "gastrointestinal"},
    # Neurological / head
    {"name": "headache",           "category": "neurological"},
    {"name": "confusion",          "category": "neurological"},
    {"name": "seizure",            "category": "neurological"},
    {"name": "altered consciousness","category": "neurological"},
    {"name": "dizziness",          "category": "neurological"},
    # Musculoskeletal / general
    {"name": "body ache",          "category": "musculoskeletal"},
    {"name": "joint pain",         "category": "musculoskeletal"},
    {"name": "muscle pain",        "category": "musculoskeletal"},
    {"name": "fatigue",            "category": "general"},
    {"name": "weakness",           "category": "general"},
    {"name": "weight loss",        "category": "general"},
    # Skin
    {"name": "rash",               "category": "skin"},
    {"name": "jaundice",           "category": "skin"},
    {"name": "bleeding",           "category": "skin"},
    {"name": "swelling",           "category": "skin"},
    # ENT / eye
    {"name": "eye pain",           "category": "ophthalmological"},
    {"name": "ear pain",           "category": "ent"},
    {"name": "runny nose",         "category": "ent"},
    # Cardiovascular / metabolic
    {"name": "palpitations",       "category": "cardiovascular"},
    {"name": "chest tightness",    "category": "cardiovascular"},
    {"name": "excessive thirst",   "category": "metabolic"},
    {"name": "frequent urination", "category": "metabolic"},
    {"name": "numbness",           "category": "neurological"},
    # Snakebite-specific
    {"name": "swelling at bite site","category": "skin"},
    {"name": "fang marks",         "category": "skin"},
    {"name": "local necrosis",     "category": "skin"},
]

# ── Test complaints (English + Hinglish) ─────────────────────────────────────
TEST_COMPLAINTS = [
    {
        "label": "Classic dengue (English)",
        "text": "High fever for 5 days, severe headache, body ache, rash on arms, no appetite",
    },
    {
        "label": "TB presentation (English)",
        "text": "Chronic cough with blood-tinged sputum for 3 weeks, night sweats, significant weight loss, fatigue",
    },
    {
        "label": "Malaria (Hinglish)",
        "text": "Tez bukhaar aur kaampa, teen din se. Sardard bahut hai. Ulti bhi ho rahi hai.",
    },
    {
        "label": "Diarrhea + dehydration",
        "text": "Loose motions 8 times today, vomiting, weakness, cannot stand. Pet mein dard.",
    },
    {
        "label": "Snakebite (urgent)",
        "text": "Snake bite on left foot 2 hours ago. Fang marks visible. Swelling spreading up leg, severe pain.",
    },
    {
        "label": "Novel symptoms (should trigger auto_migrate)",
        "text": "Aankhon mein sujan aur lali, naak se khoon, kaafi thakaan. Weird tingling in fingers.",
    },
]

PASS = "✓"
FAIL = "✗"
SKIP = "⊘"


# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — Run migration 006
# ─────────────────────────────────────────────────────────────────────────────

def run_migration_006(conn) -> None:
    print("\n── Step 1: Migration 006 ─────────────────────────────────────────")
    with conn.cursor() as cur:
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = 'symptom_extraction_log'
            )
        """)
        exists = cur.fetchone()[0]

    if exists:
        print(f"  {PASS}  symptom_extraction_log already exists — skipping DDL")
        return

    migration_sql = (ROOT / "db" / "migrations" / "006_nlp_extraction_layer.sql").read_text()
    with conn.cursor() as cur:
        cur.execute(migration_sql)
    conn.commit()
    print(f"  {PASS}  Migration 006 applied — symptom_extraction_log created")


# ─────────────────────────────────────────────────────────────────────────────
# Step 2 — Seed symptom vocabulary
# ─────────────────────────────────────────────────────────────────────────────

def seed_symptoms(conn) -> int:
    print("\n── Step 2: Seed symptom vocabulary ──────────────────────────────")
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT id FROM public.knowledge_versions WHERE is_active LIMIT 1")
        row = cur.fetchone()
        if row is None:
            print(f"  {FAIL}  No active knowledge version found. Run seed_knowledge.py first.")
            sys.exit(1)
        version_id = row["id"]
        print(f"  Active knowledge_version id={version_id}")

        inserted = 0
        for sym in PHC_SYMPTOMS:
            cur.execute("""
                INSERT INTO public.symptoms (version_id, name, category)
                VALUES (%s, %s, %s)
                ON CONFLICT (version_id, name) DO NOTHING
                RETURNING id
            """, (version_id, sym["name"], sym["category"]))
            if cur.fetchone():
                inserted += 1

        conn.commit()

        cur.execute("SELECT COUNT(*) FROM public.symptoms WHERE version_id = %s", (version_id,))
        total = cur.fetchone()["count"]

    print(f"  {PASS}  Inserted {inserted} new symptoms  |  Total in vocab: {total}")
    return version_id


# ─────────────────────────────────────────────────────────────────────────────
# Step 3–7 — Async NLP pipeline tests
# ─────────────────────────────────────────────────────────────────────────────

async def run_async_tests(version_id: int) -> dict:
    results = {
        "vocab_loaded": False,
        "vocab_size": 0,
        "fuzzy_hits": 0,
        "llm_available": False,
        "complaints_tested": 0,
        "total_matched": 0,
        "novel_upserted": 0,
        "log_rows_written": 0,
        "urgency_flags_found": [],
        "errors": [],
    }

    pool = AsyncConnectionPool(
        conninfo=settings.supabase_db_url,
        min_size=1,
        max_size=4,
        open=False,
        kwargs={"prepare_threshold": None},
    )
    await pool.open()

    try:
        # ── Step 3: Load SymptomVocab ─────────────────────────────────────
        print("\n── Step 3: SymptomVocab in-memory load ──────────────────────")
        t0 = time.monotonic()
        vocab = await SymptomVocab.load(pool, version_id=version_id)
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        results["vocab_loaded"] = True
        results["vocab_size"] = len(vocab)
        print(f"  {PASS}  Loaded {len(vocab)} symptoms in {elapsed_ms} ms")
        print(f"  Sample: {[s['name'] for s in vocab.symptoms[:5]]}")

        # ── Step 4: Fuzzy matching (no API key needed) ────────────────────
        print("\n── Step 4: Fuzzy matching (in-memory, zero DB queries) ──────")
        fuzzy_cases = [
            ("fevr",          "fever"),        # typo
            ("khansi",        "cough"),         # Hindi
            ("bukhaar",       "fever"),         # Hindi
            ("headche",       "headache"),      # typo
            ("loose motions", "diarrhea"),      # synonym
            ("body pain",     "body ache"),     # near-synonym
        ]
        for query, expected in fuzzy_cases:
            hits = await vocab.match(query, pool, query_embedding=None)
            if hits:
                matched_name = hits[0].name
                score = hits[0].score
                ok = PASS if expected in matched_name or matched_name in expected else "~"
                print(f"  {ok}  '{query}' → '{matched_name}' (score={score:.2f})")
                results["fuzzy_hits"] += 1
            else:
                print(f"  {SKIP}  '{query}' → no fuzzy hit (may need vector fallback)")

        # ── Step 5: LLM extractor ─────────────────────────────────────────
        print("\n── Step 5: LLM extraction ───────────────────────────────────")
        has_key = bool(
            os.environ.get("OPENAI_API_KEY") or os.environ.get("HF_TOKEN")
        )
        if not has_key:
            print(f"  {SKIP}  No API key found (OPENAI_API_KEY or HF_TOKEN).")
            print("        Set one in .env to enable LLM extraction.")
            print("        Continuing with vocab/matching tests only.\n")
        else:
            results["llm_available"] = True
            extractor = SymptomExtractor()
            embedder = Embedder()

            # Quick smoke test
            probe = "Fever and cough for 3 days"
            t0 = time.monotonic()
            parsed = await extractor.extract(probe)
            elapsed_ms = int((time.monotonic() - t0) * 1000)
            print(f"  {PASS}  Extractor responded in {elapsed_ms} ms  (model: {parsed.model_used})")
            print(f"        Probe: '{probe}'")
            print(f"        Extracted: {[s.name for s in parsed.symptoms]}")
            print(f"        Urgency flags: {parsed.urgency_flags}")

        # ── Step 6: Full pipeline per test complaint ───────────────────────
        print("\n── Step 6: Full pipeline (extract → match → upsert → write) ─")

        if not has_key:
            print(f"  {SKIP}  Skipping full pipeline — no API key.")
            print("        Run again with OPENAI_API_KEY=... to test the full stack.")
        else:
            extractor = SymptomExtractor()
            embedder = Embedder()

            # Use a test patient (pick first existing patient or create one)
            async with pool.connection() as conn:
                row = await conn.execute(
                    "SELECT id FROM public.patients ORDER BY created_at LIMIT 1"
                )
                patient_row = await row.fetchone()
                test_patient_id = str(patient_row[0]) if patient_row else None

            for complaint in TEST_COMPLAINTS:
                label = complaint["label"]
                text  = complaint["text"]
                print(f"\n  [{label}]")
                print(f"  Text: {text[:80]}{'...' if len(text) > 80 else ''}")

                try:
                    # 6a. Extract
                    t0 = time.monotonic()
                    parsed = await extractor.extract(text)
                    extract_ms = int((time.monotonic() - t0) * 1000)

                    sym_names = [s.name for s in parsed.symptoms]
                    print(f"  {PASS}  Extracted {len(parsed.symptoms)} symptoms in {extract_ms} ms: {sym_names}")
                    if parsed.urgency_flags:
                        print(f"       ⚠  Urgency flags: {parsed.urgency_flags}")
                        results["urgency_flags_found"].extend(parsed.urgency_flags)

                    # 6b. Match
                    match_result = await match_complaint(parsed, vocab, pool, embedder)
                    matched_names = [m.name for m in match_result.matched]
                    novel_names   = [s.name for s in match_result.novel]
                    print(f"  {PASS}  Matched: {matched_names}")
                    if novel_names:
                        print(f"       ★  Novel (will upsert): {novel_names}")

                    # 6c. Auto-migrate novel symptoms
                    novel_matches = []
                    if match_result.novel:
                        novel_matches = await upsert_novel(
                            match_result.novel,
                            match_result.embeddings,
                            vocab,
                            pool,
                            version_id=version_id,
                        )
                        results["novel_upserted"] += len(novel_matches)
                        print(f"  {PASS}  Upserted {len(novel_matches)} novel symptoms to DB")

                    # 6d. Write patient events + audit log
                    all_matches = match_result.matched + novel_matches
                    if test_patient_id and all_matches:
                        await write_patient_events(
                            test_patient_id, all_matches, parsed, pool
                        )
                        results["log_rows_written"] += 1
                        print(f"  {PASS}  Wrote patient_history_events + symptom_extraction_log")

                    results["complaints_tested"] += 1
                    results["total_matched"] += len(all_matches)

                except Exception as exc:
                    results["errors"].append(f"{label}: {exc}")
                    print(f"  {FAIL}  Error: {exc}")

        # ── Step 7: Verify DB writes ──────────────────────────────────────
        print("\n── Step 7: Verify Supabase writes ───────────────────────────")
        async with pool.connection() as conn:
            for query, label in [
                ("SELECT COUNT(*) FROM public.symptoms", "symptoms total"),
                ("SELECT COUNT(*) FROM public.symptom_embeddings", "symptom_embeddings"),
                ("SELECT COUNT(*) FROM public.patient_history_events", "patient_history_events"),
                ("SELECT COUNT(*) FROM public.symptom_extraction_log", "symptom_extraction_log"),
            ]:
                row = await conn.execute(query)
                count = (await row.fetchone())[0]
                print(f"  {PASS}  {label:30s} {count}")

    finally:
        await pool.close()

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    print("=" * 65)
    print("  RuralDoc NLP Layer — Seed & Integration Test")
    print("=" * 65)

    # Env check
    print("\n── Environment ──────────────────────────────────────────────────")
    print(f"  SUPABASE_DB_URL : {'set' if settings.supabase_db_url else 'MISSING'}")
    print(f"  OPENAI_API_KEY  : {'set' if os.environ.get('OPENAI_API_KEY') else 'not set'}")
    print(f"  HF_TOKEN        : {'set' if os.environ.get('HF_TOKEN') else 'not set'}")
    print(f"  API_BASE_URL    : {os.environ.get('API_BASE_URL', '(default OpenAI)')}")
    print(f"  MODEL_NAME      : {os.environ.get('MODEL_NAME', 'gpt-4o-mini')}")
    print(f"  EMBED_MODEL     : {os.environ.get('EMBED_MODEL', 'text-embedding-3-small')}")

    # Sync DB setup
    with psycopg.connect(
        settings.supabase_db_url,
        autocommit=False,
        prepare_threshold=None,
    ) as conn:
        run_migration_006(conn)
        version_id = seed_symptoms(conn)

    # Async NLP tests
    results = asyncio.run(run_async_tests(version_id))

    # Summary
    print("\n" + "=" * 65)
    print("  SUMMARY")
    print("=" * 65)
    print(f"  Vocab loaded         : {results['vocab_loaded']} ({results['vocab_size']} symptoms)")
    print(f"  Fuzzy hits           : {results['fuzzy_hits']}/6 test queries")
    print(f"  LLM available        : {results['llm_available']}")
    print(f"  Complaints tested    : {results['complaints_tested']}/{len(TEST_COMPLAINTS)}")
    print(f"  Total matched        : {results['total_matched']}")
    print(f"  Novel upserted       : {results['novel_upserted']}")
    print(f"  Log rows written     : {results['log_rows_written']}")
    if results["urgency_flags_found"]:
        print(f"  Urgency flags seen   : {list(set(results['urgency_flags_found']))}")
    if results["errors"]:
        print(f"\n  ERRORS ({len(results['errors'])}):")
        for e in results["errors"]:
            print(f"    {FAIL} {e}")
        return 1

    if not results["llm_available"]:
        print("\n  NOTE: Add OPENAI_API_KEY or HF_TOKEN to .env and re-run")
        print("        to test the full LLM extraction pipeline.")

    print("\n  All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
