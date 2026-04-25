"""
scripts/seed_knowledge.py — populate Layer 1 (clinical knowledge) in Supabase.

Reads from:
  • public.phc_disease_guidelines (the flat CSV import) for disease free-text
  • env.scenarios.scenarios_v2 for the canonical test / facility /
    differential vocabulary

Writes to:
  knowledge_versions, diseases, tests, facilities, vital_signs,
  disease_red_flags, disease_referrals, disease_differentials, disease_tests

Idempotent: reruns deactivate the prior version and create a fresh one tagged
with a new source_hash; it does NOT delete old rows, so every scenario/episode
written under an old version remains reproducible.

Run from project root:
    python scripts/seed_knowledge.py
"""

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

# Make the package importable when running as a script
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from db.settings import settings
from env.scenarios import scenarios_v2


# ── Canonical name normalization ─────────────────────────────────────────────
# CSV display name → list of canonical snake_case disease names that pull
# their free-text fields from that CSV row.
CSV_TO_CANONICAL: dict[str, list[str]] = {
    "Hypertension": ["hypertension"],
    "Type 2 Diabetes": ["type_2_diabetes"],
    "Malaria": ["malaria"],
    "Dengue": ["dengue"],
    "Typhoid": ["typhoid_fever"],
    "Tuberculosis (Pulmonary)": ["tuberculosis"],
    "Nutritional Anemia": ["nutritional_anemia"],
    "Diarrheal Disease with Dehydration": ["diarrheal_disease_with_dehydration"],
    "COPD / Asthma": ["asthma", "copd_exacerbation"],
    "Acute MI / Stroke": ["ischaemic_heart_disease", "stroke"],
}

VITAL_SIGNS = [
    ("temp", "°C"),
    ("bp_systolic", "mmHg"),
    ("bp_diastolic", "mmHg"),
    ("hr", "bpm"),
    ("spo2", "%"),
]


def csv_row_for(canonical: str) -> str | None:
    """Return the CSV display name whose row feeds this canonical disease."""
    for csv_name, names in CSV_TO_CANONICAL.items():
        if canonical in names:
            return csv_name
    return None


def split_red_flags(text: str) -> list[str]:
    """Split a free-text red-flags paragraph into separate clauses."""
    if not text:
        return []
    parts = re.split(r"[.,;] ", text.strip().rstrip("."))
    return [p.strip().rstrip(".") for p in parts if p.strip()]


def main() -> int:
    # 1. Source hash over scenarios + CSV source so reruns bump the version
    #    only when inputs actually change.
    source_material = json.dumps(
        {
            "scenarios_v2_ids": [s["id"] for s in scenarios_v2],
            "csv_canonical_map": CSV_TO_CANONICAL,
        },
        sort_keys=True,
    )
    source_hash = hashlib.sha256(source_material.encode()).hexdigest()[:16]
    version_label = f"v{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"

    # 2. Build canonical name sets from scenarios_v2
    canonical_diseases = sorted({s["hidden_diagnosis"] for s in scenarios_v2})
    canonical_tests = sorted({t for s in scenarios_v2 for t in s["test_costs"].keys()})
    canonical_facilities = sorted(
        {s["referral_destination"] for s in scenarios_v2 if s.get("referral_destination")}
    )

    # Also augment facilities with CSV referral_facility values
    # (fetched from DB; avoids re-parsing CSV in Python)

    print(f"[seed_knowledge] source_hash={source_hash}  label={version_label}")
    print(f"  diseases   (canonical) = {len(canonical_diseases)}")
    print(f"  tests      (canonical) = {len(canonical_tests)}")
    print(f"  facilities (from scenarios) = {len(canonical_facilities)}")

    with psycopg.connect(
        settings.supabase_db_url,
        autocommit=False,
        prepare_threshold=None,
    ) as conn:
        conn.row_factory = dict_row
        with conn.cursor() as cur:
            # ── Pre-flight: ensure scenarios.external_id column exists ──
            cur.execute(
                """
                ALTER TABLE public.scenarios
                ADD COLUMN IF NOT EXISTS external_id text;
                CREATE UNIQUE INDEX IF NOT EXISTS scenarios_external_id_uniq
                ON public.scenarios(external_id) WHERE external_id IS NOT NULL;
                """
            )

            # ── Deactivate any prior active version ──
            cur.execute(
                "UPDATE public.knowledge_versions SET is_active = false WHERE is_active;"
            )

            # ── Create new active knowledge_version ──
            cur.execute(
                """
                INSERT INTO public.knowledge_versions (label, source_hash, is_active)
                VALUES (%s, %s, true)
                RETURNING id;
                """,
                (version_label, source_hash),
            )
            version_id = cur.fetchone()["id"]
            print(f"  → knowledge_version id={version_id}")

            # ── Pull CSV rows once ──
            cur.execute("SELECT * FROM public.phc_disease_guidelines ORDER BY id;")
            csv_rows = {row["disease_name"]: row for row in cur.fetchall()}

            # Augment facilities from CSV's referral_facility column
            for r in csv_rows.values():
                fac = (r.get("referral_facility") or "").strip().rstrip(".")
                if fac and fac not in canonical_facilities:
                    canonical_facilities.append(fac)

            # ── Insert vital_signs (upsert by unique name) ──
            for name, unit in VITAL_SIGNS:
                cur.execute(
                    """
                    INSERT INTO public.vital_signs (name, unit)
                    VALUES (%s, %s)
                    ON CONFLICT (name) DO UPDATE SET unit = EXCLUDED.unit;
                    """,
                    (name, unit),
                )

            # ── Insert facilities ──
            facility_ids: dict[str, int] = {}
            for fac_name in canonical_facilities:
                # Classify tier from name
                if "District" in fac_name:
                    tier = "District"
                elif "PHC" in fac_name:
                    tier = "PHC"
                elif "Tertiary" in fac_name or "Secondary" in fac_name:
                    tier = "Tertiary"
                elif "Surgical" in fac_name:
                    tier = "Surgical"
                else:
                    tier = "Secondary"
                cur.execute(
                    """
                    INSERT INTO public.facilities (name, tier)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                    RETURNING id;
                    """,
                    (fac_name, tier),
                )
                row = cur.fetchone()
                if row is None:
                    cur.execute("SELECT id FROM public.facilities WHERE name = %s;", (fac_name,))
                    row = cur.fetchone()
                facility_ids[fac_name] = row["id"]

            # ── Insert tests (version-scoped) ──
            test_ids: dict[str, int] = {}
            for t in canonical_tests:
                cur.execute(
                    """
                    INSERT INTO public.tests (version_id, name, category, available_at_phc)
                    VALUES (%s, %s, 'phc_diagnostic', true)
                    RETURNING id;
                    """,
                    (version_id, t),
                )
                test_ids[t] = cur.fetchone()["id"]

            # ── Insert diseases (version-scoped), attaching CSV free-text ──
            disease_ids: dict[str, int] = {}
            for canonical in canonical_diseases:
                csv_name = csv_row_for(canonical)
                csv_row = csv_rows.get(csv_name) if csv_name else None
                cur.execute(
                    """
                    INSERT INTO public.diseases
                        (version_id, name, prevalence_text, evolution_text, red_flags_text)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id;
                    """,
                    (
                        version_id,
                        canonical,
                        (csv_row or {}).get("prevalence"),
                        (csv_row or {}).get("classic_evolution"),
                        (csv_row or {}).get("red_flags"),
                    ),
                )
                disease_ids[canonical] = cur.fetchone()["id"]

            # ── Insert disease_red_flags ──
            rf_count = 0
            for canonical, did in disease_ids.items():
                csv_name = csv_row_for(canonical)
                csv_row = csv_rows.get(csv_name) if csv_name else None
                if not csv_row:
                    continue
                for clause in split_red_flags(csv_row.get("red_flags") or ""):
                    cur.execute(
                        """
                        INSERT INTO public.disease_red_flags
                            (disease_id, red_flag_text, forces_referral)
                        VALUES (%s, %s, true);
                        """,
                        (did, clause),
                    )
                    rf_count += 1

            # ── Insert disease_referrals (match scenarios' referral_destination) ──
            ref_count = 0
            by_disease_facility: set[tuple[int, int]] = set()
            for s in scenarios_v2:
                fac = s.get("referral_destination")
                if not fac or not s.get("requires_referral"):
                    continue
                did = disease_ids.get(s["hidden_diagnosis"])
                fid = facility_ids.get(fac)
                if did is None or fid is None:
                    continue
                key = (did, fid)
                if key in by_disease_facility:
                    continue
                by_disease_facility.add(key)
                csv_name = csv_row_for(s["hidden_diagnosis"])
                csv_row = csv_rows.get(csv_name) if csv_name else None
                cur.execute(
                    """
                    INSERT INTO public.disease_referrals
                        (disease_id, facility_id, exact_signs, do_not_wait_reason)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (disease_id, facility_id) DO NOTHING;
                    """,
                    (
                        did,
                        fid,
                        (csv_row or {}).get("referral_exact_signs"),
                        (csv_row or {}).get("referral_do_not_wait"),
                    ),
                )
                ref_count += 1

            # ── Insert disease_tests (from scenarios: role derived) ──
            dt_count = 0
            for s in scenarios_v2:
                did = disease_ids.get(s["hidden_diagnosis"])
                if did is None:
                    continue
                for test_name in s["test_costs"].keys():
                    tid = test_ids.get(test_name)
                    if tid is None:
                        continue
                    if test_name == s.get("conclusive_test"):
                        role = "conclusive"
                        info_gain = 1.0
                    elif test_name in s.get("relevant_tests", []):
                        role = "first_line"
                        info_gain = 0.5
                    else:
                        role = "cost_efficient_combo"
                        info_gain = 0.2
                    cur.execute(
                        """
                        INSERT INTO public.disease_tests
                            (disease_id, test_id, role, info_gain)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (disease_id, test_id, role) DO NOTHING;
                        """,
                        (did, tid, role, info_gain),
                    )
                    dt_count += 1

            # ── Insert disease_differentials (best-effort from CSV overlap_mimics) ──
            diff_count = 0
            for canonical, did in disease_ids.items():
                csv_name = csv_row_for(canonical)
                csv_row = csv_rows.get(csv_name) if csv_name else None
                if not csv_row:
                    continue
                mimics_text = (csv_row.get("overlap_mimics") or "").lower()
                distinguishing = csv_row.get("overlap_distinguishing")
                for other_canonical, other_did in disease_ids.items():
                    if other_canonical == canonical:
                        continue
                    # rough token match: the canonical name stripped of _
                    token = other_canonical.split("_")[0]
                    if token and token in mimics_text:
                        cur.execute(
                            """
                            INSERT INTO public.disease_differentials
                                (disease_id, mimic_disease_id, distinguishing_feature)
                            VALUES (%s, %s, %s)
                            ON CONFLICT (disease_id, mimic_disease_id) DO NOTHING;
                            """,
                            (did, other_did, distinguishing),
                        )
                        diff_count += 1

            conn.commit()

        # ── Report ──
        with conn.cursor() as cur:
            print("\n[seed_knowledge] committed. Post-seed row counts:")
            for t in [
                "knowledge_versions", "diseases", "symptoms", "tests",
                "vital_signs", "facilities", "disease_red_flags",
                "disease_referrals", "disease_tests", "disease_differentials",
            ]:
                cur.execute(f"SELECT COUNT(*) AS c FROM public.{t};")
                print(f"  {t:24s} {cur.fetchone()['c']}")

    print("\n[seed_knowledge] done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
