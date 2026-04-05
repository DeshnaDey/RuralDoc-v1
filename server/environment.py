"""
server/environment.py — MedicalDiagnosisEnvironment

Stateful RL environment for clinical decision-making.
Wires together rewards.py and progression.py.
Public boundary uses Pydantic types from models.py;
all internal logic operates on plain dicts.
"""

import random
import sys
import os

# Allow running as `python server/environment.py` from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rewards import calculate_reward
from progression import evolve_patient, get_test_result
from scenarios.scenario2 import scenarios_v2
from models import (
    MedicalAction, MedicalActionAdapter,
    Observation, State, StepResult, action_to_dict,
    OrderTestAction, DiagnoseAction, ReferAction,
)


class MedicalDiagnosisEnvironment:
    """
    A turn-based clinical RL environment.

    Typical usage:
        env = MedicalDiagnosisEnvironment()
        obs = env.reset()
        result = env.step({"type": "order_test", "test_name": "rapid_malaria_test"})
        result = env.step({"type": "diagnose", "diagnosis": "malaria"})
    """

    def __init__(self):
        self._scenario = None
        self._current_day = 1
        self._budget = 0.0
        self._tests_ordered = []
        self._referred = False
        self._done = False
        self._memory = []
        self._last_obs = {}

    # ── reset ────────────────────────────────────────────────────────────────

    def reset(self, scenario: dict = None) -> Observation:
        """
        Start a new episode.

        Args:
            scenario: scenario dict from scenarios_v2, or None to pick randomly.

        Returns:
            Initial Observation.
        """
        self._scenario = scenario if scenario is not None else random.choice(scenarios_v2)
        self._current_day = 1
        self._budget = float(self._scenario["budget"])
        self._tests_ordered = []
        self._referred = False
        self._done = False
        self._memory = []

        initial_state = evolve_patient(self._scenario, 1)
        obs = Observation(
            patient=self._scenario["patient_demographics"],
            symptoms=initial_state["symptoms"],
            vitals=initial_state["vitals"],
            available_tests=initial_state["available_tests"],
            status=initial_state["status"],
            budget_remaining=self._budget,
            day=1,
            memory=[],
        )
        self._last_obs = obs
        return obs

    # ── step ─────────────────────────────────────────────────────────────────

    def step(self, action: dict | MedicalAction) -> StepResult:
        """
        Take one action in the environment.

        Args:
            action: plain dict or a MedicalAction Pydantic object — one of
                OrderTestAction / {"type": "order_test", "test_name": "<name>"}
                DiagnoseAction  / {"type": "diagnose",   "diagnosis": "<name>"}
                ReferAction     / {"type": "refer"}

        Returns:
            StepResult with observation, reward, done, and info.
        """
        # Convert Pydantic action to plain dict before all logic
        if isinstance(action, (OrderTestAction, DiagnoseAction, ReferAction)):
            action = action_to_dict(action)

        # 0. Done guard — episode already over
        if self._done:
            return StepResult(
                observation=self._last_obs,
                reward=0.0,
                done=True,
                info={
                    "action_taken": action,
                    "tests_ordered": list(self._tests_ordered),
                    "referred": self._referred,
                    "scenario_id": self._scenario["id"],
                },
            )

        # 1. Build current_state snapshot (budget BEFORE this action)
        current_state = {
            "current_day": self._current_day,
            "budget_remaining": self._budget,
            "tests_ordered": list(self._tests_ordered),
            "referred": self._referred,
        }

        # 2. Calculate reward
        reward = calculate_reward(current_state, action, self._scenario)

        # 3. Apply action side-effects
        action_type = action["type"]

        if action_type == "order_test":
            test_name = action["test_name"]
            cost = self._scenario["test_costs"].get(test_name, 0)
            is_duplicate = test_name in self._tests_ordered
            can_afford = self._budget >= cost

            if not is_duplicate and can_afford:
                self._budget -= cost
                self._tests_ordered.append(test_name)
                result = get_test_result(self._scenario, self._current_day, test_name)
                if result:
                    self._memory.append(result["memory_note"])

        elif action_type == "refer":
            self._referred = True

        # diagnose: no state mutation beyond done flag below

        # 4. Check done conditions (using current day status, before advancing)
        current_status = evolve_patient(self._scenario, self._current_day)["status"]
        if action_type == "diagnose" or current_status == "critical" or self._budget <= 0:
            self._done = True

        # 5. Advance day and get new patient state
        self._current_day += 1
        new_state = evolve_patient(self._scenario, self._current_day)

        # 6. Build and cache observation
        obs = Observation(
            patient=self._scenario["patient_demographics"],
            symptoms=new_state["symptoms"],
            vitals=new_state["vitals"],
            available_tests=new_state["available_tests"],
            status=new_state["status"],
            budget_remaining=self._budget,
            day=self._current_day,
            memory=list(self._memory),
        )
        self._last_obs = obs

        return StepResult(
            observation=obs,
            reward=reward,
            done=self._done,
            info={
                "action_taken": action,
                "tests_ordered": list(self._tests_ordered),
                "referred": self._referred,
                "scenario_id": self._scenario["id"],
            },
        )

    # ── state ────────────────────────────────────────────────────────────────

    def state(self) -> State:
        """Return a snapshot of the current internal environment state."""
        return State(
            current_day=self._current_day,
            budget_remaining=self._budget,
            tests_ordered=list(self._tests_ordered),
            referred=self._referred,
            done=self._done,
            scenario_id=self._scenario["id"] if self._scenario else "",
            patient_status=evolve_patient(self._scenario, self._current_day)["status"]
            if self._scenario else "stable",
        )


# ─────────────────────────────────────────────────────────────────────────────
# Smoke test — full TB episode
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    tb = next(s for s in scenarios_v2 if s["id"] == "case_01")

    env = MedicalDiagnosisEnvironment()
    SEP = "=" * 62

    print(f"\n{SEP}")
    print(" Full TB Episode — MedicalDiagnosisEnvironment smoke test")
    print(SEP)

    obs = env.reset(scenario=tb)
    print(f"\n[reset] scenario={tb['id']} day={obs.day} "
          f"budget={obs.budget_remaining} status={obs.status}")
    print(f"  patient: {obs.patient}")
    print(f"  symptoms: {obs.symptoms}")

    def run_step(label, action, expected_reward):
        result = env.step(action)
        got = result.reward
        ok = abs(got - expected_reward) < 1e-6
        flag = "PASS" if ok else "FAIL"
        print(f"\n[{flag}] {label}")
        print(f"  reward: expected={expected_reward:.4f} got={got:.4f}")
        print(f"  done={result.done} day={result.observation.day} "
              f"budget={result.observation.budget_remaining} "
              f"status={result.observation.status}")
        print(f"  tests_ordered={result.info['tests_ordered']}")
        if result.observation.memory:
            last_note = result.observation.memory[-1]
            print(f"  last_memory_note: {last_note[:70]!r}")
        return result

    # Step 1: order chest_auscultation (day 1, info_gain=0.4, cost=1)
    r1 = run_step(
        "order chest_auscultation (day 1, info_gain=0.4)",
        OrderTestAction(test_name="chest_auscultation"),
        expected_reward=-0.05 + 0.4,  # 0.35
    )

    # Step 2: order sputum_smear (day 2, info_gain=1.0, cost=6)
    r2 = run_step(
        "order sputum_smear (day 2, info_gain=1.0)",
        OrderTestAction(test_name="sputum_smear"),
        expected_reward=-0.05 + 1.0,  # 0.95
    )

    # Step 3: refer (day 3 < 14/2=7 -> early +0.2)
    r3 = run_step(
        "refer (day 3, early referral -> +0.2)",
        ReferAction(),
        expected_reward=-0.05 + 0.2,  # 0.15
    )

    # Step 4: diagnose tuberculosis (day 4, correct, referred=True)
    # reward = -0.05 + 1.0 + 0.5*(14-4)/14
    #        = -0.05 + 1.0 + 0.5*(10/14)
    expected_diag = -0.05 + 1.0 + 0.5 * (10 / 14)
    r4 = run_step(
        "diagnose tuberculosis (day 4, correct, referred)",
        DiagnoseAction(diagnosis="tuberculosis"),
        expected_reward=expected_diag,
    )

    # Verify final state
    print(f"\n{SEP}")
    s = env.state()
    budget_ok = s.budget_remaining == 24 - 1 - 6  # 17
    memory_ok = len(r4.observation.memory) == 2    # 2 tests ordered
    done_ok = s.done is True
    print(f"  [{'PASS' if budget_ok else 'FAIL'}] final budget = {s.budget_remaining} (expected 17)")
    print(f"  [{'PASS' if memory_ok else 'FAIL'}] memory notes = {len(r4.observation.memory)} (expected 2)")
    print(f"  [{'PASS' if done_ok else 'FAIL'}] done = {s.done} (expected True)")

    # Step 5: done-guard — extra step after episode ends
    r5 = env.step(OrderTestAction(test_name="blood_panel"))
    guard_ok = r5.reward == 0.0 and r5.done is True
    print(f"  [{'PASS' if guard_ok else 'FAIL'}] done-guard: reward={r5.reward} done={r5.done}")
    print()
