"""
validate.py — Pre-submission validation for RuralDocEnv.

Runs a checklist to verify the environment is submission-ready.

Usage:
    python -m env.validate
"""

import sys
import traceback
from env.scenarios import scenarios_v2, expand_daily_progression
from models import (
    OrderTestAction, DiagnoseAction, ReferAction,
    Observation, State, StepResult,
)
from env.tools import diagnostic_tools, get_all_tool_names
from env.rewards import calculate_reward
from env.progression import evolve_patient, get_test_result


PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"

results = []


def check(label: str, ok: bool, detail: str = ""):
    tag = PASS if ok else FAIL
    print(f"  [{tag}] {label}" + (f" — {detail}" if detail else ""))
    results.append(ok)


def section(title: str):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print('=' * 60)


# ── 1. Scenarios ──────────────────────────────────────────────────────────────
section("1. Scenarios")

check("scenarios_v2 has 20 entries", len(scenarios_v2) == 20,
      f"found {len(scenarios_v2)}")

required_keys = {
    "id", "hidden_diagnosis", "patient_demographics", "budget",
    "test_costs", "daily_progression", "critical_window_days",
    "requires_referral", "penalty_events", "relevant_tests", "conclusive_test",
}
for sc in scenarios_v2:
    missing = required_keys - set(sc.keys())
    check(f"scenario {sc.get('id','?')} has all required keys",
          not missing, f"missing: {missing}" if missing else "")

# ── 2. Tools ──────────────────────────────────────────────────────────────────
section("2. Diagnostic Tools")

check("diagnostic_tools has 12–15 entries",
      12 <= len(diagnostic_tools) <= 15, f"found {len(diagnostic_tools)}")

for sc in scenarios_v2:
    unknown = [t for t in sc["test_costs"] if t not in diagnostic_tools]
    check(f"scenario {sc['id']} — all test_costs are valid tool names",
          not unknown, f"unknown: {unknown}" if unknown else "")

# ── 3. Progression ────────────────────────────────────────────────────────────
section("3. Progression")

for sc in scenarios_v2:
    try:
        state = evolve_patient(sc, 1)
        check(f"scenario {sc['id']} — evolve_patient(day=1) returns valid dict",
              all(k in state for k in ("day", "symptoms", "vitals", "available_tests", "status")))
    except Exception as e:
        check(f"scenario {sc['id']} — evolve_patient(day=1)", False, str(e))

# ── 4. Rewards ────────────────────────────────────────────────────────────────
section("4. Reward function")

sc = scenarios_v2[0]
state_snap = {
    "current_day": 1,
    "budget_remaining": float(sc["budget"]),
    "tests_ordered": [],
    "referred": False,
}
try:
    r = calculate_reward(state_snap, {"type": "order_test", "test_name": sc["conclusive_test"]}, sc)
    check("calculate_reward returns a float", isinstance(r, float), f"got {type(r)}")
    check("conclusive test reward > 0", r > 0, f"reward={r:.3f}")
except Exception as e:
    check("calculate_reward smoke test", False, str(e))

# ── 5. Pydantic models ────────────────────────────────────────────────────────
section("5. Pydantic models")

try:
    obs = Observation(
        patient={"age": 30, "gender": "male", "location": "test"},
        symptoms=["fever"],
        vitals={"temp": "38C", "bp": "120/80", "hr": 80, "spo2": "98%"},
        available_tests=list(diagnostic_tools.keys())[:3],
        status="stable",
        budget_remaining=10.0,
        day=1,
        memory=[],
    )
    check("Observation model instantiates", True)
    a1 = OrderTestAction(test_name="thermometer_check")
    a2 = DiagnoseAction(diagnosis="malaria")
    a3 = ReferAction()
    check("Action models instantiate", True)
except Exception as e:
    check("Pydantic models", False, str(e))

# ── Summary ───────────────────────────────────────────────────────────────────
section("Summary")
passed = sum(results)
total = len(results)
print(f"\n  {passed}/{total} checks passed\n")

if passed < total:
    print("  ✗ Fix the failures above before submission.")
    sys.exit(1)
else:
    print("  ✓ All checks passed — environment is submission-ready.")
