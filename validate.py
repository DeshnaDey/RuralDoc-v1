"""
validate.py — Pre-submission validation for RuralDocEnv.

Checks:
    1. scenario_completeness  — all 20 scenarios have required fields
    2. test_coverage          — TOOLS covers tests referenced in scenarios
    3. reward_logic           — reward smoke-test (runs rewards.py __main__ cases)
    4. environment_integrity  — a full TB episode runs without error
    5. server_connectivity    — optional live server check (skipped with --quick)

Usage:
    python validate.py          # run all checks including server ping
    python validate.py --quick  # skip server connectivity check

Exit codes:
    0 — all checks passed
    1 — one or more checks failed
"""

from __future__ import annotations

import argparse
import sys
import traceback
from typing import Callable


# ── Check registry ────────────────────────────────────────────────────────────

CHECKS: list[tuple[str, Callable[[], list[str]]]] = []


def register(name: str):
    """Decorator to register a validation function."""
    def decorator(fn: Callable[[], list[str]]):
        CHECKS.append((name, fn))
        return fn
    return decorator


# ── Check 1: scenario completeness ───────────────────────────────────────────

@register("scenario_completeness")
def check_scenarios() -> list[str]:
    """Verify all scenarios have required fields."""
    from scenarios.scenario2 import scenarios_v2

    required_keys = {
        "id", "budget", "critical_window_days", "hidden_diagnosis",
        "daily_progression", "test_costs", "penalty_events", "patient_demographics",
    }
    errors: list[str] = []

    if len(scenarios_v2) < 3:
        errors.append(f"Expected ≥ 3 scenarios, found {len(scenarios_v2)}")

    for s in scenarios_v2:
        sid = s.get("id", "<unknown>")
        missing = required_keys - set(s.keys())
        if missing:
            errors.append(f"  [{sid}] missing keys: {sorted(missing)}")

        # penalty_events must have budget_exhausted and duplicate_test
        pe = s.get("penalty_events", {})
        for pk in ("budget_exhausted", "duplicate_test"):
            if pk not in pe:
                errors.append(f"  [{sid}] penalty_events missing '{pk}'")

        # daily_progression must be non-empty
        if not s.get("daily_progression"):
            errors.append(f"  [{sid}] daily_progression is empty")

        # budget must be positive
        if s.get("budget", 0) <= 0:
            errors.append(f"  [{sid}] budget must be > 0, got {s.get('budget')}")

    return errors


# ── Check 2: test coverage ────────────────────────────────────────────────────

@register("test_coverage")
def check_test_coverage() -> list[str]:
    """Verify that TOOLS covers every test referenced in scenarios."""
    from scenarios.scenario2 import scenarios_v2
    from tools import TOOLS

    errors: list[str] = []
    tool_names = set(TOOLS.keys())
    scenario_tests: set[str] = set()

    for s in scenarios_v2:
        scenario_tests.update(s.get("test_costs", {}).keys())

    missing = scenario_tests - tool_names
    for t in sorted(missing):
        errors.append(f"  Test '{t}' referenced in scenarios but not in TOOLS")

    return errors


# ── Check 3: reward logic ─────────────────────────────────────────────────────

@register("reward_logic")
def check_reward_logic() -> list[str]:
    """Run a set of reward spot-checks."""
    from scenarios.scenario2 import scenarios_v2
    from rewards import calculate_reward

    errors: list[str] = []
    malaria = next(s for s in scenarios_v2 if s["id"] == "case_07")  # Malaria, window=2
    tb = next(s for s in scenarios_v2 if s["id"] == "case_01")      # TB, window=14

    cases = [
        # (label, state, action, scenario, expected)
        (
            "order_test info_gain",
            {"current_day": 1, "budget_remaining": 14.0, "tests_ordered": [], "referred": False},
            {"type": "order_test", "test_name": "thermometer_check"},
            malaria,
            -0.05 + 0.3,
        ),
        (
            "duplicate_test penalty",
            {"current_day": 1, "budget_remaining": 14.0, "tests_ordered": ["thermometer_check"], "referred": False},
            {"type": "order_test", "test_name": "thermometer_check"},
            malaria,
            -0.05 + malaria["penalty_events"]["duplicate_test"],
        ),
        (
            "correct diagnose within window",
            {"current_day": 1, "budget_remaining": 14.0, "tests_ordered": [], "referred": False},
            {"type": "diagnose", "diagnosis": "malaria"},
            malaria,
            -0.05 + 1.0 + 0.5 * (1 / 2),
        ),
        (
            "early referral TB",
            {"current_day": 1, "budget_remaining": 24.0, "tests_ordered": [], "referred": False},
            {"type": "refer"},
            tb,
            -0.05 + 0.2,
        ),
    ]

    for label, state, action, scenario, expected in cases:
        got = calculate_reward(state, action, scenario)
        if abs(got - expected) > 1e-6:
            errors.append(f"  [{label}] expected={expected:.6f} got={got:.6f}")

    return errors


# ── Check 4: environment integrity ────────────────────────────────────────────

@register("environment_integrity")
def check_environment() -> list[str]:
    """Run a minimal episode through MedicalDiagnosisEnvironment."""
    from scenarios.scenario2 import scenarios_v2
    from server.environment import MedicalDiagnosisEnvironment

    errors: list[str] = []
    tb = next((s for s in scenarios_v2 if s["id"] == "case_01"), None)
    if tb is None:
        errors.append("  case_01 (TB) not found in scenarios_v2")
        return errors

    try:
        env = MedicalDiagnosisEnvironment()
        obs = env.reset(scenario=tb)
        assert obs.day == 1
        assert obs.budget_remaining == tb["budget"]

        r = env.step({"type": "order_test", "test_name": "chest_auscultation"})
        assert not r.done
        assert r.observation.day == 2

        r = env.step({"type": "refer"})
        assert not r.done

        r = env.step({"type": "diagnose", "diagnosis": "tuberculosis"})
        assert r.done
        assert r.reward > 0, f"Expected positive reward, got {r.reward}"

        s = env.state()
        assert s.done

    except Exception as exc:
        errors.append(f"  Exception during episode: {exc}")
        errors.append(textwrap.indent(traceback.format_exc(), "    "))

    return errors


# ── Check 5: server connectivity (optional) ───────────────────────────────────

def check_server() -> list[str]:
    """Ping the running server (skipped with --quick)."""
    import os
    try:
        import httpx
    except ImportError:
        return ["  httpx not installed; install dev extras: pip install httpx"]

    url = os.getenv("ENV_URL", "http://localhost:8000")
    errors: list[str] = []
    try:
        resp = httpx.get(f"{url}/health", timeout=5.0)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "ok":
            errors.append(f"  /health returned unexpected body: {data}")
    except Exception as exc:
        errors.append(f"  Cannot reach {url}/health: {exc}")
    return errors


# ── Runner ────────────────────────────────────────────────────────────────────

import textwrap


def run_checks(quick: bool = False) -> bool:
    """Run all registered checks. Return True if all pass."""
    all_pass = True

    check_list = list(CHECKS)
    if not quick:
        check_list.append(("server_connectivity", check_server))

    for name, fn in check_list:
        try:
            errors = fn()
        except Exception as exc:
            errors = [f"  Unexpected exception: {exc}"]

        if errors:
            status = "FAIL"
            all_pass = False
        else:
            status = "PASS"

        print(f"[{status}] {name}")
        for err in errors:
            print(err)

    return all_pass


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate RuralDocEnv before submission.")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Skip the server connectivity check (useful in CI without a running server).",
    )
    args = parser.parse_args()

    print("=" * 60)
    print(" RuralDocEnv — pre-submission validation")
    print("=" * 60)
    print()

    passed = run_checks(quick=args.quick)
    print()
    print("=" * 60)
    print("Result:", "ALL CHECKS PASSED" if passed else "SOME CHECKS FAILED")
    print("=" * 60)

    sys.exit(0 if passed else 1)
