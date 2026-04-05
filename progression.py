"""
progression.py — Patient progression for MedicalDiagnosisEnv.

evolve_patient(scenario, current_day) -> dict
get_test_result(scenario, current_day, test_name) -> dict | None
"""

from scenarios.scenario2 import expand_daily_progression


def _get_day_state(scenario: dict, current_day: int) -> dict:
    """Return the progression state for current_day, clamped to max defined day."""
    expanded = expand_daily_progression(scenario["daily_progression"])
    max_day = max(expanded.keys())
    return expanded.get(current_day, expanded[max_day])


def _get_status(scenario: dict, current_day: int) -> str:
    """
    Return patient status based on day relative to critical window.

    stable:    current_day < critical_window_days / 2
    worsening: current_day >= critical_window_days / 2
               AND current_day <= critical_window_days
    critical:  current_day > critical_window_days
    """
    critical_window = scenario["critical_window_days"]
    if current_day > critical_window:
        return "critical"
    elif current_day >= critical_window / 2:
        return "worsening"
    else:
        return "stable"


def evolve_patient(scenario: dict, current_day: int) -> dict:
    """
    Return the patient's current observable state for the given day.

    Args:
        scenario:    scenario dict from scenarios_v2
        current_day: 1-indexed episode day

    Returns:
        {
            "day":             int,
            "symptoms":        list[str],
            "vitals":          dict (temp, bp, hr, spo2),
            "available_tests": list[str],   # all tests the agent can order
            "status":          str,         # "stable" | "worsening" | "critical"
        }
    """
    day_state = _get_day_state(scenario, current_day)
    return {
        "day":             current_day,
        "symptoms":        day_state["symptoms"],
        "vitals":          day_state["vitals"],
        "available_tests": list(scenario["test_costs"].keys()),
        "status":          _get_status(scenario, current_day),
    }


def get_test_result(scenario: dict, current_day: int, test_name: str) -> dict | None:
    """
    Return the full test result dict for a given test on a given day.

    Args:
        scenario:    scenario dict from scenarios_v2
        current_day: 1-indexed episode day
        test_name:   name of the test to look up

    Returns:
        {result, info_gain, suggests, rules_out, memory_note}
        or None if test_name is not in this scenario's test list.
    """
    day_state = _get_day_state(scenario, current_day)
    return day_state["test_results"].get(test_name, None)


# ─────────────────────────────────────────────────────────────────────────────
#  Smoke tests — all 3 scenarios
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from scenarios.scenario2 import scenarios_v2

    malaria = scenarios_v2[0]   # case_07 — Malaria,  window=2
    typhoid = scenarios_v2[1]   # case_10 — Typhoid,  window=4
    tb      = scenarios_v2[2]   # case_01 — TB,       window=14

    SEP = "=" * 62

    def check_status(label, scenario, day, expected_status):
        state = evolve_patient(scenario, day)
        got = state["status"]
        status = "PASS" if got == expected_status else "FAIL"
        print(f"  [{status}] {label}")
        if got != expected_status:
            print(f"         expected={expected_status!r}  got={got!r}")

    def check_test(label, scenario, day, test_name, expect_none=False):
        result = get_test_result(scenario, day, test_name)
        if expect_none:
            ok = result is None
            print(f"  [{'PASS' if ok else 'FAIL'}] {label} -> None")
        else:
            ok = result is not None
            print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
            if ok:
                print(f"         info_gain={result['info_gain']}  note={result['memory_note'][:60]!r}")

    # ── Malaria (window=2, window/2=1.0) ─────────────────────────────────────
    print(f"\n{SEP}")
    print(f"  Malaria case_07  |  window=2  |  window/2=1.0")
    print(SEP)

    # day 1: 1 >= 1.0 -> worsening (not stable)
    check_status("day 1 -> worsening  (1 >= 1.0)", malaria, 1, "worsening")
    # day 2: 2 >= 1.0 and 2 <= 2 -> worsening
    check_status("day 2 -> worsening  (2 <= window=2)", malaria, 2, "worsening")
    # day 3: 3 > 2 -> critical (clamped to day 2 state)
    check_status("day 3 -> critical   (3 > window=2, clamped)", malaria, 3, "critical")

    state = evolve_patient(malaria, 1)
    print(f"\n  day-1 symptoms:   {state['symptoms']}")
    print(f"  day-1 vitals:     {state['vitals']}")
    print(f"  available_tests:  {state['available_tests']}")

    check_test("get_test_result: rapid_malaria_test day-1", malaria, 1, "rapid_malaria_test")
    check_test("get_test_result: unknown_test -> None",     malaria, 1, "xray", expect_none=True)

    # ── Typhoid (window=4, window/2=2.0) ─────────────────────────────────────
    print(f"\n{SEP}")
    print(f"  Typhoid case_10  |  window=4  |  window/2=2.0")
    print(SEP)

    check_status("day 1 -> stable     (1 < 2.0)", typhoid, 1, "stable")
    check_status("day 2 -> worsening  (2 >= 2.0)", typhoid, 2, "worsening")
    check_status("day 4 -> worsening  (4 <= window=4)", typhoid, 4, "worsening")
    check_status("day 5 -> critical   (5 > window=4, clamped)", typhoid, 5, "critical")

    # clamped state: day 5 should return day-4 symptoms
    state_d4 = evolve_patient(typhoid, 4)
    state_d5 = evolve_patient(typhoid, 5)
    clamped_ok = state_d4["symptoms"] == state_d5["symptoms"]
    print(f"\n  [{'PASS' if clamped_ok else 'FAIL'}] day-5 symptoms clamped == day-4 symptoms")

    check_test("get_test_result: widal_test day-2",      typhoid, 2, "widal_test")
    check_test("get_test_result: widal_test day-4",      typhoid, 4, "widal_test")

    # ── TB (window=14, window/2=7.0) ─────────────────────────────────────────
    print(f"\n{SEP}")
    print(f"  TB case_01       |  window=14  |  window/2=7.0")
    print(SEP)

    check_status("day 6  -> stable    (6 < 7.0)", tb, 6, "stable")
    check_status("day 7  -> worsening (7 >= 7.0)", tb, 7, "worsening")
    check_status("day 14 -> worsening (14 <= window=14)", tb, 14, "worsening")
    check_status("day 15 -> critical  (15 > window=14, clamped)", tb, 15, "critical")

    # clamped state: day 15 should return day-14 symptoms
    state_d14 = evolve_patient(tb, 14)
    state_d15 = evolve_patient(tb, 15)
    clamped_ok = state_d14["symptoms"] == state_d15["symptoms"]
    print(f"\n  [{'PASS' if clamped_ok else 'FAIL'}] day-15 symptoms clamped == day-14 symptoms")

    check_test("get_test_result: sputum_smear day-1",    tb, 1, "sputum_smear")
    check_test("get_test_result: sputum_smear day-10",   tb, 10, "sputum_smear")
    check_test("get_test_result: blood_panel  day-7",    tb, 7,  "blood_panel")
