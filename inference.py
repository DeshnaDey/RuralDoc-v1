"""
inference.py — LLM agent loop for MedicalDiagnosisEnvironment.

Runs a single episode (or a batch) by sending structured observations to an
LLM and parsing its JSON action response back into the environment.

Usage:
    python inference.py                        # random scenario
    python inference.py --scenario case_01     # specific scenario
    python inference.py --all                  # all 20 scenarios, prints summary
"""

import json
import argparse
import sys
import os
import openai

sys.path.insert(0, os.path.dirname(__file__))

API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME   = os.environ.get("MODEL_NAME", "gpt-4o-mini")

from server.environment import MedicalDiagnosisEnvironment
from models import Observation
from scenarios.scenario2 import scenarios_v2


# ─────────────────────────────────────────────────────────────────────────────
#  SYSTEM PROMPT
#  This prompt is injected once at the start of every episode. It gives the
#  LLM agent its role, constraints, reasoning strategy, and the exact JSON
#  formats for all three action types.
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """
You are RuralDoc — an AI clinical decision-support agent embedded in a
primary-care simulation for rural India. Your role is to act as a first-contact
physician operating under strict resource constraints: limited diagnostic budget,
a narrow treatment window before a patient's condition deteriorates, and the
obligation to refer cases that require specialist or hospital-level care.

─────────────────────────────────────────────────────────────────────────────
YOUR GOAL
─────────────────────────────────────────────────────────────────────────────
Reach the correct diagnosis as quickly and cheaply as possible, while:
  1. Ordering only the tests most likely to narrow the differential.
  2. Referring the patient before the critical window closes (if the case
     requires a higher facility).
  3. Committing to a final diagnosis once you have sufficient evidence.

─────────────────────────────────────────────────────────────────────────────
WHAT YOU RECEIVE EACH TURN
─────────────────────────────────────────────────────────────────────────────
You will receive a structured observation block containing:

  PATIENT       — age, gender, geographic location (cues for endemic disease)
  DAY           — current episode day (1-indexed). Each action advances the day.
  STATUS        — stable | worsening | critical
                  • worsening: day >= critical_window / 2
                  • critical:  day > critical_window (episode may end)
  BUDGET        — integer units remaining. Tests have costs. Ordering a test
                  you cannot afford, or ordering the same test twice,
                  incurs a penalty.
  SYMPTOMS      — current presenting complaints (may escalate over time)
  VITALS        — temperature, blood pressure, heart rate, SpO2
  AVAILABLE TESTS — list of test names you may order, with their unit costs
  MEMORY        — your cumulative clinical chart. Every test you have ordered
                  this episode has added one memory note here. Treat this as
                  your only reliable record — you have no other memory of
                  past turns.

─────────────────────────────────────────────────────────────────────────────
HOW TO REASON (think step-by-step before each action)
─────────────────────────────────────────────────────────────────────────────

Step 1 — READ MEMORY FIRST
  Before anything else, read every note in the MEMORY block. These are the
  clinical findings you have already established. Do not re-order a test
  that already has a memory note — it is a duplicate and will be penalised.

Step 2 — BUILD YOUR DIFFERENTIAL
  Based on patient demographics, location (endemic zone?), symptoms, vitals,
  and all memory notes, list the 2–3 most likely diagnoses. Consider:
    • Geographic context: tribal/forest fringe → malaria/kala-azar;
      post-flood → hepatitis A/E; endemic districts → filariasis, leprosy.
    • Chronicity: days of illness before presentation.
    • Alarm features: hemoptysis, altered sensorium, chest pain with radiation,
      sudden hemiplegia, SpO2 < 92%.

Step 3 — SELECT THE NEXT BEST TEST
  Ask: which un-ordered test would most narrow my differential given my budget?
    • Prioritise tests likely to have high diagnostic yield for your top
      differential.
    • Avoid cheap noise tests (temperature checks, urine dipstick) when you
      already have high-yield options available — the step penalty makes
      wasteful steps costly.
    • Never order a test already in your MEMORY.
    • If budget is very low (≤ 3 units), only order if absolutely necessary;
      otherwise move to diagnosis or referral.

Step 4 — DECIDE ON REFERRAL
  Refer before diagnosing if:
    • The scenario involves a condition requiring hospital-level care
      (e.g. active TB → DOTS centre, stroke → thrombolysis window,
      acute MI → cardiac emergency, kala-azar → AmBisome infusion,
      severe paediatric pneumonia → oxygen and IV antibiotics).
    • STATUS is "worsening" or "critical".
    • Any MEMORY note contains the word "URGENT" or references a penalty
      event (e.g. hemoptysis, shock, perforation risk).
  Refer early: referral before the halfway point of the critical window
  yields a higher reward than late referral.

Step 5 — DIAGNOSE WHEN READY
  Commit to a diagnosis when:
    • A conclusive test memory note explicitly confirms a diagnosis, OR
    • Your memory notes collectively rule out all alternatives and the
      clinical picture is unambiguous.
  Use the exact hidden diagnosis string format (snake_case, e.g.
  "tuberculosis", "malaria", "type_2_diabetes", "kala_azar").
  Do not guess early — a wrong diagnosis ends the episode with no reward.
  Do not delay unnecessarily — every extra day costs a step penalty and
  risks the patient reaching critical status.

─────────────────────────────────────────────────────────────────────────────
ACTION FORMAT — respond with ONLY a single JSON object, no other text
─────────────────────────────────────────────────────────────────────────────

Order a diagnostic test:
  {"type": "order_test", "test_name": "<exact_test_name_from_available_tests>"}

Refer the patient to a higher facility:
  {"type": "refer"}

Commit to a final diagnosis (ends the episode):
  {"type": "diagnose", "diagnosis": "<exact_diagnosis_string>"}

─────────────────────────────────────────────────────────────────────────────
COMMON DIAGNOSIS STRINGS (use exactly as shown)
─────────────────────────────────────────────────────────────────────────────
tuberculosis              malaria                   dengue
typhoid_fever             type_2_diabetes           hypertension
ischaemic_heart_disease   nutritional_anemia        intestinal_worms
diarrheal_disease_with_dehydration                  asthma
copd_exacerbation         stroke                    hepatitis_a_or_e
lymphatic_filariasis      leprosy                   cervical_cancer
chronic_kidney_disease    kala_azar                 severe_pneumonia_under_5

─────────────────────────────────────────────────────────────────────────────
REWARD REMINDERS (internalise these)
─────────────────────────────────────────────────────────────────────────────
• Every action costs -0.05 step penalty. Be efficient.
• Ordering a test: reward = -0.05 + info_gain (info_gain is 0.0 to 1.0).
  Conclusive tests yield info_gain = 1.0.
• Duplicate test: -0.05 + (-0.2) = -0.25. Never re-order.
• Cannot afford test: -0.05 + (-0.5) = -0.55. Check budget before ordering.
• Correct diagnosis in window: +1.0 + 0.5 × (days_remaining / window).
• Late diagnosis OR referral omitted when required: scenario-specific
  penalty of -1.0 applied on top.
• Early referral (before window / 2): +0.15 net. Late referral: +0.05 net.

─────────────────────────────────────────────────────────────────────────────
EXAMPLE REASONING TRACE (TB scenario, day 1)
─────────────────────────────────────────────────────────────────────────────

MEMORY: (empty)

Patient: 34-year-old male, urban slum Delhi.
Symptoms: chronic cough 3 weeks, night sweats, weight loss, evening fever 37.9C.
Status: stable. Budget: 24. Day: 1.

Step 1 — Memory is empty; no prior results.
Step 2 — Differential: TB (top), chronic bronchitis, kala-azar.
         Night sweats + weight loss + evening fever in Delhi slum = classic TB.
Step 3 — Best test: chest_auscultation (cost 1) to assess apical involvement,
         then sputum_smear (cost 6) for confirmation.
         Order chest_auscultation first; preserve budget for sputum_smear.
Step 4 — Referral needed if TB confirmed (requires DOTS centre).
         Not yet — wait for at least one test result.
Step 5 — Not yet ready to diagnose; no confirmatory test done.

Action: {"type": "order_test", "test_name": "chest_auscultation"}
"""


# ─────────────────────────────────────────────────────────────────────────────
#  Observation → prompt string renderer
# ─────────────────────────────────────────────────────────────────────────────

def render_observation(obs: Observation, test_costs: dict) -> str:
    """
    Convert an Observation into the structured text block sent to the LLM
    as the user turn. Includes test costs inline so the agent can budget.
    """
    lines = [
        "═" * 62,
        f"  DAY {obs.day}  |  STATUS: {obs.status.upper()}  |  "
        f"BUDGET REMAINING: {obs.budget_remaining:.0f} units",
        "═" * 62,
        "",
        "PATIENT",
        f"  Age: {obs.patient.get('age')}  "
        f"Gender: {obs.patient.get('gender')}  "
        f"Location: {obs.patient.get('location')}",
        "",
        "SYMPTOMS",
    ]
    for s in obs.symptoms:
        lines.append(f"  • {s}")

    lines += [
        "",
        "VITALS",
        f"  Temp: {obs.vitals.get('temp')}  "
        f"BP: {obs.vitals.get('bp')}  "
        f"HR: {obs.vitals.get('hr')} bpm  "
        f"SpO2: {obs.vitals.get('spo2')}",
        "",
        "AVAILABLE TESTS  (name — cost)",
    ]
    for t in obs.available_tests:
        cost = test_costs.get(t, "?")
        lines.append(f"  • {t}  [{cost} units]")

    lines += ["", "MEMORY (your clinical chart from this episode)"]
    if obs.memory:
        for i, note in enumerate(obs.memory, 1):
            lines.append(f"  [{i}] {note}")
    else:
        lines.append("  (no tests ordered yet)")

    lines += [
        "",
        "─" * 62,
        "Respond with a single JSON action object.",
        "─" * 62,
    ]
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
#  LLM call (stub — replace with your inference backend)
# ─────────────────────────────────────────────────────────────────────────────

def call_llm(system_prompt: str, conversation: list[dict]) -> str:
    """Send the conversation to the configured OpenAI-compatible endpoint."""
    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        raise ValueError("HF_TOKEN environment variable is not set.")
    client = openai.OpenAI(base_url=API_BASE_URL, api_key=hf_token)
    messages = [{"role": "system", "content": system_prompt}] + conversation
    response = client.chat.completions.create(
        model=MODEL_NAME,
        max_tokens=256,
        messages=messages,
    )
    return response.choices[0].message.content


# ─────────────────────────────────────────────────────────────────────────────
#  Action parser
# ─────────────────────────────────────────────────────────────────────────────

def parse_action(raw_text: str) -> dict | None:
    """
    Parse a JSON action dict from the LLM's raw text response.
    Returns None if no valid action can be extracted.
    """
    raw_text = raw_text.strip()
    # Try the whole response first
    try:
        action = json.loads(raw_text)
        if isinstance(action, dict) and "type" in action:
            return action
    except json.JSONDecodeError:
        pass
    # Fall back: find the first {...} block in the text
    start = raw_text.find("{")
    end   = raw_text.rfind("}") + 1
    if start != -1 and end > start:
        try:
            action = json.loads(raw_text[start:end])
            if isinstance(action, dict) and "type" in action:
                return action
        except json.JSONDecodeError:
            pass
    return None


# ─────────────────────────────────────────────────────────────────────────────
#  Single episode runner
# ─────────────────────────────────────────────────────────────────────────────

def run_episode(scenario: dict = None, verbose: bool = True) -> dict:
    """
    Run one full episode with the LLM agent.

    Args:
        scenario: scenario dict or None (random).
        verbose:  if True, print each turn to stdout.

    Returns:
        {
          "scenario_id":    str,
          "diagnosis":      str | None,   # agent's final diagnosis
          "correct":        bool,
          "total_reward":   float,
          "steps":          int,
          "referred":       bool,
          "budget_spent":   float,
        }
    """
    env = MedicalDiagnosisEnvironment()
    obs = env.reset(scenario=scenario)
    sc  = env._scenario

    conversation:  list[dict] = []
    total_reward   = 0.0
    steps          = 0
    final_diagnosis = None
    max_steps      = sc["critical_window_days"] * 2 + 5  # safety cap

    if verbose:
        print(f"\n{'#' * 62}")
        print(f"  SCENARIO: {sc['id']}  |  {sc['hidden_diagnosis'].upper()}")
        print(f"  Difficulty: {sc['difficulty_tier']}  |  "
              f"Budget: {sc['budget']}  |  "
              f"Critical window: {sc['critical_window_days']} days")
        print(f"{'#' * 62}")

    done         = False
    step_rewards: list[float] = []
    success      = False

    print(f"[START] task={sc['id']} env=rural_diagnosis model={MODEL_NAME}")

    try:
        while not done and steps < max_steps:
            # Render observation as user turn
            user_text = render_observation(obs, sc["test_costs"])
            conversation.append({"role": "user", "content": user_text})

            if verbose:
                print(f"\n{user_text}")

            # Call LLM
            try:
                raw_response = call_llm(SYSTEM_PROMPT, conversation)
            except Exception as e:
                error_msg = str(e)
                action = {"type": "diagnose", "diagnosis": "unknown"}
                step_rewards.append(-0.05)
                steps += 1
                print(f"[STEP] step={steps} action={json.dumps(action)} reward=-0.05 done=true error={error_msg}")
                success = False
                break

            conversation.append({"role": "assistant", "content": raw_response})

            if verbose:
                print(f"\n  LLM → {raw_response.strip()}")

            # Parse action
            action = parse_action(raw_response)
            if action is None:
                if verbose:
                    print("  [WARN] Could not parse action from LLM response. Skipping.")
                # Inject a fallback to avoid infinite loop
                action = {"type": "diagnose", "diagnosis": "unknown"}

            if action["type"] == "diagnose":
                final_diagnosis = action.get("diagnosis")

            # Step environment
            result        = env.step(action)
            total_reward += result.reward
            steps        += 1
            done          = result.done
            obs           = result.observation
            step_rewards.append(result.reward)

            action_str = json.dumps(action, separators=(',', ':'))
            print(f"[STEP] step={steps} action={action_str} reward={result.reward:.2f} "
                  f"done={'true' if done else 'false'} error=null")

            if verbose:
                print(f"  reward={result.reward:+.4f}  cumulative={total_reward:+.4f}  "
                      f"done={done}  day={obs.day}  budget={obs.budget_remaining:.0f}")

        state   = env.state()
        correct = final_diagnosis == sc["hidden_diagnosis"]
        success = correct
        budget_spent = sc["budget"] - state.budget_remaining
    finally:
        rewards_str = ",".join(f"{r:.2f}" for r in step_rewards)
        score = max(0.001, min(0.999, sum(step_rewards) / 10.0))
        print(f"[END] success={'true' if success else 'false'} steps={steps} score={score:.3f} rewards={rewards_str}")

    summary = {
        "scenario_id":   sc["id"],
        "diagnosis":     final_diagnosis,
        "hidden":        sc["hidden_diagnosis"],
        "correct":       correct,
        "total_reward":  round(total_reward, 4),
        "steps":         steps,
        "referred":      state.referred,
        "budget_spent":  budget_spent,
    }

    if verbose:
        print(f"\n{'─' * 62}")
        print(f"  EPISODE SUMMARY")
        print(f"{'─' * 62}")
        for k, v in summary.items():
            print(f"  {k:20s}: {v}")
        print()

    return summary


# ─────────────────────────────────────────────────────────────────────────────
#  Batch runner
# ─────────────────────────────────────────────────────────────────────────────

def run_all(verbose: bool = False) -> None:
    """Run all 20 scenarios and print a results table."""
    results = []
    for sc in scenarios_v2:
        try:
            r = run_episode(scenario=sc, verbose=verbose)
            results.append(r)
        except NotImplementedError:
            print("[ERROR] call_llm() not implemented. Cannot run batch.")
            return

    print(f"\n{'=' * 72}")
    print(f"  BATCH RESULTS — {len(results)} scenarios")
    print(f"{'=' * 72}")
    header = f"{'ID':10s} {'Difficulty':8s} {'Correct':8s} {'Reward':8s} {'Steps':6s} {'Referred':9s} {'Spent':6s}"
    print(f"\n  {header}")
    print(f"  {'─' * 66}")
    for r in results:
        sc_obj = next(s for s in scenarios_v2 if s["id"] == r["scenario_id"])
        print(
            f"  {r['scenario_id']:10s} "
            f"{sc_obj['difficulty_tier']:8s} "
            f"{'YES' if r['correct'] else 'NO':8s} "
            f"{r['total_reward']:+8.3f} "
            f"{r['steps']:6d} "
            f"{'YES' if r['referred'] else 'NO':9s} "
            f"{r['budget_spent']:6.0f}"
        )

    correct_count = sum(1 for r in results if r["correct"])
    avg_reward    = sum(r["total_reward"] for r in results) / len(results)
    print(f"\n  Correct diagnoses: {correct_count}/{len(results)}")
    print(f"  Average reward:    {avg_reward:+.3f}")
    print()


# ─────────────────────────────────────────────────────────────────────────────
#  CLI entrypoint
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="RuralDoc LLM agent runner")
    parser.add_argument(
        "--scenario", type=str, default=None,
        help="Scenario ID to run (e.g. case_01). Omit for random."
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Run all 20 scenarios and print a summary table."
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Suppress per-turn output (summary only)."
    )
    args = parser.parse_args()

    if args.all:
        run_all(verbose=not args.quiet)
    else:
        if args.scenario:
            sc = next((s for s in scenarios_v2 if s["id"] == args.scenario), None)
            if sc is None:
                print(f"[ERROR] Unknown scenario ID: {args.scenario}")
                print(f"  Valid IDs: {[s['id'] for s in scenarios_v2]}")
                sys.exit(1)
            run_episode(scenario=sc, verbose=not args.quiet)
        else:
            for scenario_id in ("case_07", "case_10", "case_01"):
                sc = next((s for s in scenarios_v2 if s["id"] == scenario_id), None)
                if sc is None:
                    print(f"[ERROR] Unknown scenario ID: {scenario_id}")
                    sys.exit(1)
                run_episode(scenario=sc, verbose=not args.quiet)


if __name__ == "__main__":
    main()
