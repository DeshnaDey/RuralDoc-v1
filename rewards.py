"""
rewards.py — Reward function for MedicalDiagnosisEnv.

calculate_reward(current_state, action, scenario) -> float

current_state keys:
    current_day      : int   — 1-indexed episode day
    budget_remaining : float — budget left BEFORE this action
    tests_ordered    : list  — test names ordered in prior steps (not this one)
    referred         : bool  — whether agent has already taken the refer action

action shapes:
    {"type": "order_test", "test_name": "<name>"}
    {"type": "diagnose",   "diagnosis": "<name>"}
    {"type": "refer"}

scenario: standard dict from scenarios_v2 (scenarios/scenario2.py).
"""

from scenarios.scenario2 import expand_daily_progression

# Penalty keys that are structural (not scenario-specific clinical events)
_STANDARD_PENALTY_KEYS = {"budget_exhausted", "duplicate_test"}


def _get_scenario_penalty_key(penalty_events: dict) -> str | None:
    """Return the first scenario-specific named penalty key (not budget/duplicate)."""
    for key in penalty_events:
        if key not in _STANDARD_PENALTY_KEYS:
            return key
    return None


def calculate_reward(current_state: dict, action: dict, scenario: dict) -> float:
    """
    Compute single-step reward given the current state, the action taken,
    and the active scenario.

    Returns a float reward. Negative values are penalties; positive are rewards.
    """
    reward = -0.05  # step penalty — encourage efficiency

    action_type = action["type"]
    day = current_state["current_day"]
    budget = current_state["budget_remaining"]
    tests_ordered = current_state["tests_ordered"]
    referred = current_state.get("referred", False)
    penalty_events = scenario["penalty_events"]

    if action_type == "order_test":
        test_name = action["test_name"]

        # Duplicate test check
        if test_name in tests_ordered:
            reward += penalty_events["duplicate_test"]
            return reward

        # Budget exhaustion check (can't afford this test)
        test_cost = scenario["test_costs"].get(test_name, 0)
        if budget < test_cost:
            reward += penalty_events["budget_exhausted"]
            return reward

        # Info gain from current day's test result
        expanded = expand_daily_progression(scenario["daily_progression"])
        max_day = max(expanded.keys())
        day_state = expanded.get(day, expanded[max_day])
        test_result = day_state["test_results"].get(test_name, {})
        info_gain = test_result.get("info_gain", 0.0)
        reward += info_gain

    elif action_type == "diagnose":
        correct = action["diagnosis"] == scenario["hidden_diagnosis"]

        if correct:
            reward += 1.0
            # Early diagnosis bonus: scaled by how much of the window remains
            critical_window = scenario["critical_window_days"]
            days_remaining = critical_window - day
            if days_remaining > 0:
                reward += 0.5 * (days_remaining / critical_window)

        # Scenario-specific penalty: apply once if late OR referral omitted
        critical_window = scenario["critical_window_days"]
        late = day > critical_window
        referral_omitted = scenario["requires_referral"] and not referred
        if late or referral_omitted:
            penalty_key = _get_scenario_penalty_key(penalty_events)
            if penalty_key is not None:
                reward += penalty_events[penalty_key]

    elif action_type == "refer":
        if scenario["requires_referral"]:
            critical_window = scenario["critical_window_days"]
            if day < critical_window / 2:
                reward += 0.2  # early referral
            else:
                reward += 0.1  # late but still valid

    return reward


# ─────────────────────────────────────────────────────────────────────────────
# Smoke tests — uses the malaria scenario (case_07, easy) from scenario2.py
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from scenarios.scenario2 import scenarios_v2

    malaria = scenarios_v2[0]  # case_07 — Malaria (P. vivax), budget=14, window=2
    tb = scenarios_v2[2]       # case_01 — Pulmonary TB, budget=24, window=14, requires_referral=True

    def run(label, state, action, scenario, expected):
        got = calculate_reward(state, action, scenario)
        status = "PASS" if abs(got - expected) < 1e-9 else "FAIL"
        print(f"[{status}] {label}")
        print(f"  expected={expected:.4f} got={got:.4f}\n")

    print("=" * 60)
    print(" MedicalDiagnosisEnv — rewards.py smoke tests")
    print("=" * 60, "\n")

    base_state = {
        "current_day": 1,
        "budget_remaining": 14.0,
        "tests_ordered": [],
        "referred": False,
    }

    # 1. Order thermometer_check on day 1 — info_gain 0.3
    run(
        "order_test: thermometer_check day-1 (info_gain=0.3)",
        {**base_state},
        {"type": "order_test", "test_name": "thermometer_check"},
        malaria,
        expected=-0.05 + 0.3,  # 0.25
    )

    # 2. Duplicate test
    run(
        "order_test: thermometer_check DUPLICATE",
        {**base_state, "tests_ordered": ["thermometer_check"]},
        {"type": "order_test", "test_name": "thermometer_check"},
        malaria,
        expected=-0.05 + (-0.2),  # -0.25
    )

    # 3. Order rapid_malaria_test on day 1 — conclusive, info_gain 1.0
    run(
        "order_test: rapid_malaria_test day-1 (info_gain=1.0)",
        {**base_state, "tests_ordered": ["thermometer_check"]},
        {"type": "order_test", "test_name": "rapid_malaria_test"},
        malaria,
        expected=-0.05 + 1.0,  # 0.95
    )

    # 4. Budget exhausted — only 2 left, blood_panel costs 5
    run(
        "order_test: blood_panel — budget exhausted (have 2, need 5)",
        {**base_state, "budget_remaining": 2.0},
        {"type": "order_test", "test_name": "blood_panel"},
        malaria,
        expected=-0.05 + (-0.5),  # -0.55
    )

    # 5. Correct diagnosis within critical window (day 1, window=2)
    # +1.0 correct + 0.5*(2-1)/2 early bonus
    run(
        "diagnose: malaria on day-1 (correct, within window)",
        {**base_state},
        {"type": "diagnose", "diagnosis": "malaria"},
        malaria,
        expected=-0.05 + 1.0 + 0.5 * (1 / 2),  # 1.20
    )

    # 6. Correct diagnosis after critical window (day 3, window=2)
    # +1.0 correct, no early bonus (days_remaining=-1), +scenario penalty (-1.0)
    run(
        "diagnose: malaria on day-3 (correct but LATE, past window=2)",
        {**base_state, "current_day": 3},
        {"type": "diagnose", "diagnosis": "malaria"},
        malaria,
        expected=-0.05 + 1.0 + (-1.0),  # -0.05
    )

    # 7. Wrong diagnosis within window — no correct bonus, no late penalty
    run(
        "diagnose: typhoid (wrong) on day-1 — no bonus, no late penalty",
        {**base_state},
        {"type": "diagnose", "diagnosis": "typhoid"},
        malaria,
        expected=-0.05,  # -0.05
    )

    # 8. TB: refer early (day 1, critical_window=14, day < 7) -> +0.2
    run(
        "refer: TB scenario day-1 (early, requires_referral=True) -> +0.2",
        {**base_state, "current_day": 1},
        {"type": "refer"},
        tb,
        expected=-0.05 + 0.2,  # 0.15
    )

    # 9. TB: refer late (day 8, critical_window=14, day >= 7) -> +0.1
    run(
        "refer: TB scenario day-8 (late, requires_referral=True) -> +0.1",
        {**base_state, "current_day": 8},
        {"type": "refer"},
        tb,
        expected=-0.05 + 0.1,  # 0.05
    )

    # 10. Malaria: refer (requires_referral=False) — no bonus
    run(
        "refer: malaria scenario (requires_referral=False) — no bonus",
        {**base_state},
        {"type": "refer"},
        malaria,
        expected=-0.05,  # -0.05
    )

    # 11. TB: diagnose correctly on day 3, NOT referred -> referral_omitted penalty (-1.0)
    # days_remaining = 14-3=11 -> early bonus = 0.5*(11/14) ≈ 0.3929
    run(
        "diagnose: TB correct day-3, not referred -> referral penalty fires",
        {**base_state, "current_day": 3, "budget_remaining": 24.0, "referred": False},
        {"type": "diagnose", "diagnosis": "tuberculosis"},
        tb,
        expected=-0.05 + 1.0 + 0.5 * (11 / 14) + (-1.0),
    )

    # 12. TB: diagnose correctly on day 3, already referred -> no referral penalty
    run(
        "diagnose: TB correct day-3, already referred -> no referral penalty",
        {**base_state, "current_day": 3, "budget_remaining": 24.0, "referred": True},
        {"type": "diagnose", "diagnosis": "tuberculosis"},
        tb,
        expected=-0.05 + 1.0 + 0.5 * (11 / 14),
    )

    # 13. TB: both late AND not referred — penalty applied only once
    run(
        "diagnose: TB correct day-15 (late) + not referred — penalty once",
        {**base_state, "current_day": 15, "budget_remaining": 24.0, "referred": False},
        {"type": "diagnose", "diagnosis": "tuberculosis"},
        tb,
        expected=-0.05 + 1.0 + 0.0 + (-1.0),  # no early bonus (days_remaining<0), penalty once
    )
