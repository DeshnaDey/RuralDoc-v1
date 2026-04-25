"""
scripts/seed_scenarios.py — populate Layer 3 (scenarios + progression) in Supabase.

Assumes seed_knowledge.py has already been run and the active knowledge
version has all the disease / test / facility rows we need to FK to.

Writes:
  scenarios, scenario_test_costs, scenario_relevant_tests, scenario_penalties,
  progression_events

Idempotent: rebuilds Layer 3 under the current active knowledge_version.
Deletes existing scenario rows for the current active version first, then
reseeds. Episodes FK to scenarios via ON DELETE RESTRICT, so if any episodes
exist this script will refuse to reseed until they're archived. (Safe default.)

Run from project root:
    python scripts/seed_scenarios.py
"""

import json
import sys
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from db.settings import settings
from env.scenarios import scenarios_v2


def parse_day_range(key: str) -> tuple[int, int]:
    """Parse a daily_progression key like '1-7' or '3' → (start, end)."""
    s = str(key)
    if "-" in s:
        a, b = s.split("-")
        return int(a), int(b)
    n = int(s)
    return n, n


def main() -> int:
    with psycopg.connect(
        settings.supabase_db_url,
        autocommit=False,
        # Supabase's transaction pooler (:6543) can't share prepared statements
        # across reused backends — disable them.
        prepare_threshold=None,
    ) as conn:
        conn.row_factory = dict_row

        with conn.cursor() as cur:
            # ── Active knowledge version ──
            cur.execute(
                "SELECT id FROM public.knowledge_versions WHERE is_active LIMIT 1;"
            )
            row = cur.fetchone()
            if row is None:
                print("[seed_scenarios] ABORT: no active knowledge_version. "
                      "Run scripts/seed_knowledge.py first.")
                return 1
            kv_id = row["id"]

            # ── Refuse to wipe if episodes exist under this version ──
            cur.execute(
                "SELECT COUNT(*) AS c FROM public.episodes WHERE knowledge_version_id = %s;",
                (kv_id,),
            )
            ep_count = cur.fetchone()["c"]
            if ep_count:
                print(f"[seed_scenarios] ABORT: {ep_count} episodes exist for "
                      f"knowledge_version {kv_id}. Archive them first or cut a "
                      f"new version via seed_knowledge.py.")
                return 2

            # ── Clear prior scenarios under this version (cascades to children) ──
            cur.execute(
                "DELETE FROM public.scenarios WHERE knowledge_version_id = %s;",
                (kv_id,),
            )

            # ── Build lookup maps for this version ──
            cur.execute(
                "SELECT id, name FROM public.diseases WHERE version_id = %s;",
                (kv_id,),
            )
            disease_by_name = {r["name"]: r["id"] for r in cur.fetchall()}

            cur.execute(
                "SELECT id, name FROM public.tests WHERE version_id = %s;",
                (kv_id,),
            )
            test_by_name = {r["name"]: r["id"] for r in cur.fetchall()}

            cur.execute("SELECT id, name FROM public.facilities;")
            facility_by_name = {r["name"]: r["id"] for r in cur.fetchall()}

            # ── Insert scenarios ──
            scenario_uuids: dict[str, str] = {}
            event_count = 0
            for s in scenarios_v2:
                did = disease_by_name.get(s["hidden_diagnosis"])
                if did is None:
                    print(f"  skip {s['id']} — disease {s['hidden_diagnosis']!r} not in knowledge layer")
                    continue
                fid = facility_by_name.get(s.get("referral_destination"))

                cur.execute(
                    """
                    INSERT INTO public.scenarios
                        (knowledge_version_id, disease_id, external_id, difficulty,
                         budget, critical_window_days, referral_facility_id,
                         penalty_config)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                    RETURNING id;
                    """,
                    (
                        kv_id,
                        did,
                        s["id"],
                        s.get("difficulty_tier"),
                        s["budget"],
                        s["critical_window_days"],
                        fid,
                        json.dumps(s.get("penalty_events", {})),
                    ),
                )
                sid = cur.fetchone()["id"]
                scenario_uuids[s["id"]] = sid

                # ── scenario_test_costs ──
                for tname, cost in s.get("test_costs", {}).items():
                    tid = test_by_name.get(tname)
                    if tid is None:
                        continue
                    cur.execute(
                        """
                        INSERT INTO public.scenario_test_costs (scenario_id, test_id, cost)
                        VALUES (%s, %s, %s);
                        """,
                        (sid, tid, cost),
                    )

                # ── scenario_relevant_tests ──
                relevant = set(s.get("relevant_tests", []))
                conclusive = s.get("conclusive_test")
                for tname in set(relevant) | ({conclusive} if conclusive else set()):
                    tid = test_by_name.get(tname)
                    if tid is None:
                        continue
                    cur.execute(
                        """
                        INSERT INTO public.scenario_relevant_tests
                            (scenario_id, test_id, is_conclusive)
                        VALUES (%s, %s, %s);
                        """,
                        (sid, tid, tname == conclusive),
                    )

                # ── scenario_penalties ──
                for event_name, delta in s.get("penalty_events", {}).items():
                    cur.execute(
                        """
                        INSERT INTO public.scenario_penalties
                            (scenario_id, event_name, reward_delta)
                        VALUES (%s, %s, %s);
                        """,
                        (sid, event_name, delta),
                    )

                # ── progression_events ──
                # For each phase, emit:
                #   - one symptom_onset per symptom @ day_offset=start
                #   - one test_result per test @ day_offset=start (payload has range)
                # Vital shifts are encoded as payload on a single status_transition
                # at the start of each phase.
                for day_key, phase in s.get("daily_progression", {}).items():
                    start_day, end_day = parse_day_range(day_key)

                    for symptom_text in phase.get("symptoms", []):
                        cur.execute(
                            """
                            INSERT INTO public.progression_events
                                (scenario_id, day_offset, event_type, payload, branch_condition)
                            VALUES (%s, %s, 'symptom_onset', %s::jsonb, '{}'::jsonb);
                            """,
                            (sid, start_day, json.dumps({"text": symptom_text, "through_day": end_day})),
                        )
                        event_count += 1

                    cur.execute(
                        """
                        INSERT INTO public.progression_events
                            (scenario_id, day_offset, event_type, payload, branch_condition)
                        VALUES (%s, %s, 'status_transition', %s::jsonb, '{}'::jsonb);
                        """,
                        (
                            sid,
                            start_day,
                            json.dumps({"vitals": phase.get("vitals", {}), "through_day": end_day}),
                        ),
                    )
                    event_count += 1

                    for tname, result in phase.get("test_results", {}).items():
                        tid = test_by_name.get(tname)
                        cur.execute(
                            """
                            INSERT INTO public.progression_events
                                (scenario_id, day_offset, event_type, test_id,
                                 payload, branch_condition, info_gain, memory_note,
                                 suggests, rules_out)
                            VALUES (%s, %s, 'test_result', %s, %s::jsonb, '{}'::jsonb,
                                    %s, %s, %s::jsonb, %s::jsonb);
                            """,
                            (
                                sid,
                                start_day,
                                tid,
                                json.dumps({"result": result.get("result"), "through_day": end_day}),
                                result.get("info_gain"),
                                result.get("memory_note"),
                                json.dumps(result.get("suggests", [])),
                                json.dumps(result.get("rules_out", [])),
                            ),
                        )
                        event_count += 1

            conn.commit()

        # ── Report ──
        with conn.cursor() as cur:
            print(f"[seed_scenarios] committed. knowledge_version_id={kv_id}")
            for t in [
                "scenarios", "scenario_test_costs", "scenario_relevant_tests",
                "scenario_penalties", "progression_events",
            ]:
                cur.execute(f"SELECT COUNT(*) AS c FROM public.{t};")
                print(f"  {t:28s} {cur.fetchone()['c']}")

    print("[seed_scenarios] done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
