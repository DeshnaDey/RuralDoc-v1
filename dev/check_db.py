"""
dev/check_db.py — Smoke test for the Supabase connection.

Verifies that:
    1. .env is loaded and SUPABASE_DB_URL is reachable.
    2. We can open a connection and run a trivial query.
    3. The schema from migrations/001_init_schema.sql is in place.
    4. pgvector is enabled.

Run from the project root:
    python dev/check_db.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db.pool import close_pool, get_conn


EXPECTED_TABLES = {
    "knowledge_versions",
    "diseases",
    "symptoms",
    "tests",
    "vital_signs",
    "facilities",
    "disease_symptoms",
    "disease_tests",
    "disease_differentials",
    "disease_vital_patterns",
    "disease_red_flags",
    "disease_referrals",
    "disease_embeddings",
    "symptom_embeddings",
    "patients",
    "patient_conditions",
    "patient_allergies",
    "patient_history_events",
    "patient_embeddings",
    "scenarios",
    "scenario_test_costs",
    "scenario_relevant_tests",
    "scenario_penalties",
    "progression_events",
    "case_embeddings",
    "episodes",
    "episode_steps",
    "patient_encounters",
}


async def main() -> int:
    try:
        async with get_conn() as conn:
            async with conn.cursor() as cur:
                # 1. Trivial connectivity
                await cur.execute("SELECT 1;")
                assert (await cur.fetchone()) == (1,)
                print("✓ Connected to Supabase")

                # 2. Schema landed
                await cur.execute(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                    ORDER BY table_name;
                    """
                )
                found = {row[0] for row in await cur.fetchall()}
                missing = EXPECTED_TABLES - found
                extra = found - EXPECTED_TABLES

                print(f"✓ Found {len(found)} tables in public")
                if missing:
                    print(f"✗ Missing {len(missing)}: {sorted(missing)}")
                if extra:
                    print(f"  (extra, probably fine): {sorted(extra)}")

                # 3. pgvector
                await cur.execute(
                    "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"
                )
                row = await cur.fetchone()
                if row:
                    print(f"✓ pgvector {row[1]} enabled")
                else:
                    print("✗ pgvector NOT enabled — toggle it in Dashboard → Database → Extensions")

                # 4. Row counts (all zero right now, but proves we can read)
                await cur.execute(
                    """
                    SELECT 'diseases' AS t, COUNT(*) FROM public.diseases
                    UNION ALL SELECT 'scenarios', COUNT(*) FROM public.scenarios
                    UNION ALL SELECT 'episodes', COUNT(*) FROM public.episodes;
                    """
                )
                print("\nRow counts:")
                for table_name, count in await cur.fetchall():
                    print(f"  {table_name:12s} {count}")

        return 0 if not missing else 1
    finally:
        await close_pool()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
