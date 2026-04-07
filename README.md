# RuralDoc 🏥

**A reinforcement-learning environment for clinical decision-making in resource-constrained rural India.**

RuralDoc simulates a primary-care physician working in a low-resource setting. An LLM agent receives patient observations — symptoms, vitals, and prior test memory — and must decide which diagnostic tests to order, when to refer the patient to a higher facility, and when to commit to a final diagnosis. The environment rewards efficient, timely, and clinically sound decisions while penalising waste, delay, and missed referrals.

---

## Table of Contents

- [Overview](#overview)
- [Repository Structure](#repository-structure)
- [Environment Design](#environment-design)
  - [Actions](#actions)
  - [Observations](#observations)
  - [Reward Function](#reward-function)
  - [Patient Progression](#patient-progression)
- [Scenarios](#scenarios)
  - [Difficulty Tiers](#difficulty-tiers)
  - [Test Results Schema](#test-results-schema)
- [Quickstart](#quickstart)
- [Running the Smoke Tests](#running-the-smoke-tests)
- [LLM Agent (inference.py)](#llm-agent-inferencepy)
- [Adding New Scenarios](#adding-new-scenarios)

---

## Overview

The motivating problem is that AI-assisted clinical decision support for rural and tribal health workers is constrained by three realities that urban benchmarks ignore:

1. **Budget** — every diagnostic test has a real unit cost. Over-testing is penalised.
2. **Time** — diseases progress. Each day without a correct diagnosis or referral narrows the treatment window.
3. **Referral logic** — some conditions can only be managed at a district hospital. Failing to refer is a patient-safety event.

RuralDoc encodes all three pressures into a single reward signal and exposes a clean gym-like API for any RL or LLM-based agent to interact with.

---

## Repository Structure

```
RuralDoc/
├── models.py                  # Pydantic types: actions, observations, states
├── rewards.py                 # Reward function (calculate_reward)
├── progression.py             # Patient state evolution (evolve_patient, get_test_result)
├── scenarios/
│   └── scenario2.py           # All 20 disease scenarios (scenarios_v2)
├── server/
│   └── environment.py         # MedicalDiagnosisEnvironment — the main env class
└── inference.py               # LLM agent loop (system prompt + step-by-step runner)
```

---

## Environment Design

### Actions

The agent can take one of three action types per step:

| Action | Dict format | When to use |
|---|---|---|
| `OrderTestAction` | `{"type": "order_test", "test_name": "<n>"}` | Request a diagnostic test; costs budget units |
| `DiagnoseAction` | `{"type": "diagnose", "diagnosis": "<name>"}` | Commit to a final diagnosis; ends the episode |
| `ReferAction` | `{"type": "refer"}` | Refer the patient to a higher facility |

Available test names for a scenario are listed in `observation.available_tests` and priced in `scenario["test_costs"]`.

### Observations

Each call to `reset()` and `step()` returns an `Observation` object:

```python
class Observation(BaseModel):
    patient:          dict        # age, gender, location
    symptoms:         list[str]   # current presenting complaints
    vitals:           dict        # temp, bp, hr, spo2
    available_tests:  list[str]   # tests the agent may order
    status:           str         # "stable" | "worsening" | "critical"
    budget_remaining: float       # units left
    day:              int         # current episode day (1-indexed)
    memory:           list[str]   # clinical memory notes from ordered tests
```

`memory` is the agent's scratchpad — every time a test is ordered, its `memory_note` is appended. The note is written as a clinician would chart it and is the agent's only persistent record across steps.

### Reward Function

`rewards.py::calculate_reward` returns a float reward for each step:

```
Every step:       -0.05   (step penalty — encourages efficiency)

order_test:
  duplicate test:          + penalty_events["duplicate_test"]     (typically -0.2)
  cannot afford:           + penalty_events["budget_exhausted"]   (typically -0.5)
  affordable + unique:     + info_gain   (0.0 to 1.0 from test_results)

diagnose:
  correct:                 + 1.0
  correct + days remaining in window:  + 0.5 * (days_remaining / critical_window)
  late (past window) OR referral omitted when required:
                           + scenario-specific penalty (typically -1.0)

refer:
  scenario requires_referral = True:
    day < critical_window / 2:   + 0.2   (early referral)
    day >= critical_window / 2:  + 0.1   (late but valid)
  scenario requires_referral = False:  no bonus
```

The episode ends when the agent calls `diagnose`, the patient status becomes `critical`, or the budget is exhausted.

### Patient Progression

`progression.py` maps each day to a symptom/vitals snapshot defined in `daily_progression`. Day ranges (e.g. `"1-7"`) are expanded to individual days by `expand_daily_progression`. When the current day exceeds the last defined day, the final state is clamped and patient status becomes `critical`.

Patient status thresholds:

```
stable:    current_day < critical_window_days / 2
worsening: current_day >= critical_window_days / 2  AND  <= critical_window_days
critical:  current_day > critical_window_days
```

---

## Scenarios

`scenarios/scenario2.py` contains 20 disease scenarios (`scenarios_v2`) covering the leading causes of morbidity in rural India:

| ID | Difficulty | Diagnosis |
|---|---|---|
| case_01 | hard | Pulmonary Tuberculosis |
| case_02 | easy | Type 2 Diabetes |
| case_03 | easy | Hypertension |
| case_04 | hard | Ischaemic Heart Disease (Acute MI) |
| case_05 | easy | Nutritional Anaemia |
| case_06 | medium | Diarrheal Disease with Dehydration |
| case_07 | easy | Malaria (P. vivax) |
| case_08 | medium | Dengue Fever |
| case_09 | hard | COPD Exacerbation |
| case_10 | medium | Typhoid Fever |
| case_11 | hard | Stroke |
| case_12 | medium | Hepatitis A or E |
| case_13 | medium | Asthma |
| case_14 | hard | Lymphatic Filariasis |
| case_15 | medium | Leprosy |
| case_16 | hard | Cervical Cancer |
| case_17 | hard | Chronic Kidney Disease |
| case_18 | hard | Kala-Azar (Visceral Leishmaniasis) |
| case_19 | medium | Severe Pneumonia (Under 5) |
| case_20 | easy | Intestinal Worms |

### Difficulty Tiers

- **Easy** — 1–2 tests yield high `info_gain`, no referral required, long critical window.
- **Medium** — 3–4 tests needed to build a case, mild time pressure, some referrals.
- **Hard** — Ambiguous early findings, referral mandatory, critical window as short as 1 day. Expensive conclusive tests (e.g. `sputum_smear`) are the only path to diagnosis.

### Test Results Schema

Every test in a scenario's master list appears in every time period:

```python
"test_name": {
    "result":      str,         # clinical finding written as a doctor would chart it
    "info_gain":   float,       # 0.0–1.0; how much this test narrows the diagnosis
    "suggests":    list[str],   # conditions this result points toward
    "rules_out":   list[str],   # conditions this result excludes
    "memory_note": str          # one-sentence clinical note added to obs.memory
}
```

**`info_gain` rules:**

| Range | Meaning |
|---|---|
| `0.0` | Completely irrelevant but still executable; `rules_out` justifies running it |
| `0.05–0.2` | Weak, non-specific signal |
| `0.3–0.5` | Suspicious; meaningfully narrows the differential |
| `0.8–1.0` | Near-conclusive or conclusive |
| `1.0` | The `conclusive_test` always scores exactly 1.0 in every phase |

Phase-2 `info_gain` values are always higher than phase-1 for the same test (disease progression makes findings more dramatic), with the exception of the conclusive test which is 1.0 in both phases.

---

## Quickstart

```python
from server.environment import MedicalDiagnosisEnvironment
from models import OrderTestAction, DiagnoseAction, ReferAction

env = MedicalDiagnosisEnvironment()

# Start a random episode
obs = env.reset()
print(obs.patient, obs.symptoms, obs.vitals)

# Order a test
result = env.step(OrderTestAction(test_name="rapid_malaria_test"))
print(result.reward, result.observation.memory)

# Commit to a diagnosis
result = env.step(DiagnoseAction(diagnosis="malaria"))
print(result.reward, result.done)
```

To run a specific scenario:

```python
from scenarios.scenario2 import scenarios_v2

tb = next(s for s in scenarios_v2 if s["id"] == "case_01")
obs = env.reset(scenario=tb)
```

Plain dicts are also accepted by `step()`:

```python
env.step({"type": "order_test", "test_name": "sputum_smear"})
env.step({"type": "refer"})
env.step({"type": "diagnose", "diagnosis": "tuberculosis"})
```

---

## Running the Smoke Tests

Each module contains a self-contained smoke test runnable from the project root:

```bash
# Pydantic types and action round-trips
python models.py

# Reward function — 13 labelled PASS/FAIL tests
python rewards.py

# Patient progression — status thresholds and test lookups
python progression.py

# Full TB episode through the environment
python server/environment.py

# LLM agent inference loop
python inference.py
```

---

## LLM Agent (inference.py)

`inference.py` runs a multi-turn LLM agent against the environment. On each turn, the agent receives the current observation rendered as structured text and responds with a JSON action. The system prompt instructs the agent on:

- How to interpret `obs.memory` as a cumulative clinical chart
- Budget-aware test selection (ordering high `info_gain` tests first)
- Referral timing relative to `critical_window_days`
- The exact JSON formats for all three action types

See `inference.py` for the full system prompt and step loop.

---

## Adding New Scenarios

1. Add a new dict to `scenarios_v2` in `scenarios/scenario2.py` following the schema.
2. Ensure every test in `test_costs` appears in every `daily_progression` phase under `test_results`.
3. Set `sum(test_costs.values()) < budget` — tight but achievable.
4. Set `conclusive_test` `info_gain = 1.0` in all phases.
5. Verify Phase-2 `info_gain` > Phase-1 for non-conclusive tests.
6. Run `python scenarios/scenario2.py` to validate.

---

## Design Philosophy

RuralDoc is intentionally grounded in the real constraints of India's rural health system:

- **Tests are not free.** Every diagnostic choice has an opportunity cost.
- **Time kills.** A correct diagnosis on day 15 is worth less than one on day 3.
- **Referral is a clinical act.** Sending a patient to a district hospital at the right time — and not too late — is itself a reward-bearing decision.
- **Memory is finite.** The agent has no implicit recall of past steps. Only what was explicitly charted in `obs.memory` carries forward.
