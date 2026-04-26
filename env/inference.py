"""
inference.py — LLM agent loop for MedicalDiagnosisEnvironment.

Runs a single episode (or a batch) by sending structured observations to an
LLM and parsing its JSON action response back into the environment. Supports
any OpenAI-compatible endpoint via environment variables.

RAG layer:
    When SUPABASE_DB_URL is set, a PgRAGEngine is automatically initialised.
    On each turn the current observation is embedded and the top-k most
    relevant disease guidelines are injected into the next prompt under
    "CLINICAL CONTEXT". Set RAG_K (default 3) or DISABLE_RAG=1 to control.

Environment variables:
    HF_TOKEN        — API key / HuggingFace token (required)
    API_BASE_URL    — OpenAI-compatible base URL (default: https://api.openai.com/v1)
    MODEL_NAME      — model identifier (default: gpt-4o-mini)
    SUPABASE_DB_URL — Postgres URI (enables RAG + episode persistence)
    RAG_K           — disease hits per RAG call (default: 3)
    DISABLE_RAG     — set to 1 to disable RAG

Usage:
    python -m env.inference                     # 3 default cases
    python -m env.inference --scenario case_01
    python -m env.inference --all
    python -m env.inference --quiet
    python -m env.inference --no-rag
"""

from __future__ import annotations

import asyncio
import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import argparse
import logging
import os
import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from env.environment import MedicalDiagnosisEnvironment
from models import Observation
from env.scenarios import scenarios_v2

log = logging.getLogger("ruraldoc.inference")

API_BASE_URL = "https://api-inference.huggingface.co/v1"
MODEL_NAME   = "meta-llama/Llama-3.1-8B-Instruct"
RAG_K        = int(os.environ.get("RAG_K", "3"))


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
  2. Referring the patient before the critical window closes (if required).
  3. Committing to a final diagnosis once you have sufficient evidence.

─────────────────────────────────────────────────────────────────────────────
WHAT YOU RECEIVE EACH TURN
─────────────────────────────────────────────────────────────────────────────
  PATIENT       — age, gender, geographic location
  DAY           — current episode day (1-indexed)
  STATUS        — stable | worsening | critical
  BUDGET        — integer units remaining
  SYMPTOMS      — current presenting complaints
  VITALS        — temperature, blood pressure, heart rate, SpO2
  AVAILABLE TESTS — test names with unit costs
  MEMORY        — cumulative clinical chart from this episode
  CLINICAL CONTEXT (optional) — retrieved guidelines; use to support reasoning

─────────────────────────────────────────────────────────────────────────────
HOW TO REASON
─────────────────────────────────────────────────────────────────────────────
Step 1 — READ MEMORY FIRST. Never re-order a test already in memory.
Step 2 — BUILD DIFFERENTIAL (2–3 diagnoses) using demographics, location,
          symptoms, vitals, memory.
Step 3 — SELECT NEXT BEST TEST. Highest diagnostic yield for budget remaining.
Step 4 — DECIDE ON REFERRAL if hospital-level care is needed or STATUS is
          worsening/critical.
Step 5 — DIAGNOSE when conclusive evidence exists.

─────────────────────────────────────────────────────────────────────────────
ACTION FORMAT — respond with ONLY a single JSON object
─────────────────────────────────────────────────────────────────────────────
  {"type": "order_test", "test_name": "<exact_test_name>"}
  {"type": "refer"}
  {"type": "diagnose", "diagnosis": "<exact_diagnosis_string>"}

─────────────────────────────────────────────────────────────────────────────
COMMON DIAGNOSIS STRINGS
─────────────────────────────────────────────────────────────────────────────
tuberculosis  malaria  dengue  typhoid_fever  type_2_diabetes  hypertension
ischaemic_heart_disease  nutritional_anemia  intestinal_worms  asthma
copd_exacerbation  stroke  hepatitis_a_or_e  lymphatic_filariasis  leprosy
cervical_cancer  chronic_kidney_disease  kala_azar  severe_pneumonia_under_5
diarrheal_disease_with_dehydration

─────────────────────────────────────────────────────────────────────────────
REWARD REMINDERS
─────────────────────────────────────────────────────────────────────────────
• Every action: -0.05 step penalty.
• Conclusive test: info_gain up to 1.0. Duplicate test: -0.25. Can't afford: -0.55.
• Correct diagnosis in window: +1.0 + 0.5×(days_remaining/window).
• Early referral: +0.15 net. Late referral: +0.05 net.
"""


def render_observation(
    obs: Observation,
    test_costs: dict,
    rag_snippets: list[str] | None = None,
) -> str:
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
        lines.append(f"  • {t}  [{test_costs.get(t, '?')} units]")

    lines += ["", "MEMORY (your clinical chart from this episode)"]
    if obs.memory:
        for i, note in enumerate(obs.memory, 1):
            lines.append(f"  [{i}] {note}")
    else:
        lines.append("  (no tests ordered yet)")

    if rag_snippets:
        lines += ["", "CLINICAL CONTEXT (retrieved guidelines — use to support reasoning)"]
        for i, snippet in enumerate(rag_snippets, 1):
            lines.append(f"  [{i}] {snippet}")

    lines += ["", "─" * 62, "Respond with a single JSON action object.", "─" * 62]
    return "\n".join(lines)


def _build_rag_query(obs: Observation) -> str:
    """Build a short natural-language query from an Observation for the RAG engine."""
    patient = obs.patient or {}
    parts: list[str] = []
    parts.extend(obs.symptoms[:4])
    age    = patient.get("age")
    gender = patient.get("gender", "")
    loc    = patient.get("location", "")
    if age:
        parts.append(f"{age}{gender[0].upper() if gender else ''}")
    if loc:
        parts.append(loc)
    if obs.status and obs.status != "stable":
        parts.append(obs.status)
    return "  ".join(parts)


def call_llm(system_prompt: str, conversation: list[dict]) -> str:
    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        raise ValueError("HF_TOKEN not set")

    model = "meta-llama/Llama-3.1-8B-Instruct"
    url = furl = "https://api-inference.huggingface.co/models/meta-llama/Llama-3.1-8B-Instruct"

    headers = {
        "Authorization": f"Bearer {hf_token}",
        "Content-Type": "application/json",
    }

    # Convert chat → single prompt (HF expects plain text)
    prompt = system_prompt + "\n\n"

    for msg in conversation:
        role = msg["role"]
        content = msg["content"]

        if role == "user":
            prompt += f"User: {content}\n"
        elif role == "assistant":
            prompt += f"Assistant: {content}\n"

    prompt += "Assistant:"

    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 256,
            "temperature": 0.7,
        }
    }

    with httpx.Client(timeout=60) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    return data[0]["generated_text"].split("Assistant:")[-1].strip()


def parse_action(raw_text: str) -> dict | None:
    raw_text = raw_text.strip()
    try:
        action = json.loads(raw_text)
        if isinstance(action, dict) and "type" in action:
            return action
    except json.JSONDecodeError:
        pass
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


async def run_episode(
    scenario: dict = None,
    verbose: bool = True,
    rag_engine=None,
) -> dict:
    """
    Run one full episode with the LLM agent.

    Args:
        scenario:    scenario dict or None (random).
        verbose:     print full observation and LLM response each turn.
        rag_engine:  PgRAGEngine instance or None (no retrieval overhead).
    """
    env = MedicalDiagnosisEnvironment()
    obs = env.reset(scenario=scenario)
    sc  = env._scenario

    conversation:   list[dict] = []
    total_reward    = 0.0
    steps           = 0
    final_diagnosis = None
    step_rewards:   list[float] = []
    success         = False
    max_steps       = sc["critical_window_days"] * 2 + 5

    if verbose:
        print(f"\n{'#' * 62}")
        print(f"  SCENARIO: {sc['id']}  |  {sc['hidden_diagnosis'].upper()}")
        print(f"  Difficulty: {sc['difficulty_tier']}  |  Budget: {sc['budget']}  |  Window: {sc['critical_window_days']} days")
        print(f"  RAG: {'PgRAGEngine(k=' + str(RAG_K) + ')' if rag_engine else 'disabled'}")
        print(f"{'#' * 62}")

    print(f"[START] task={sc['id']} env=rural_diagnosis model={MODEL_NAME}")

    done        = False
    pending_rag: list[str] = []

    # Retrieve context for turn 1 from the reset observation
    if rag_engine is not None:
        try:
            ctx = await rag_engine.retrieve(_build_rag_query(obs), k=RAG_K)
            pending_rag = ctx.snippets or []
            if verbose and pending_rag:
                print(f"  [RAG] hits={ctx.meta.get('hits', 0)}")
        except Exception as exc:
            log.warning("RAG initial retrieve failed: %s", exc)

    try:
        while not done and steps < max_steps:
            user_text = render_observation(obs, sc["test_costs"], rag_snippets=pending_rag or None)
            conversation.append({"role": "user", "content": user_text})
            pending_rag = []

            if verbose:
                print(f"\n{user_text}")

            try:
                raw_response = call_llm(SYSTEM_PROMPT, conversation)
            except Exception as e:
                action = {"type": "diagnose", "diagnosis": "unknown"}
                step_rewards.append(-0.05)
                steps += 1
                print(f"[STEP] step={steps} action={json.dumps(action, separators=(',', ':'))} reward=-0.05 done=true error={e}")
                break

            conversation.append({"role": "assistant", "content": raw_response})
            if verbose:
                print(f"\n  LLM → {raw_response.strip()}")

            action = parse_action(raw_response)
            if action is None:
                if verbose:
                    print("  [WARN] Could not parse action. Skipping.")
                action = {"type": "diagnose", "diagnosis": "unknown"}

            if action["type"] == "diagnose":
                final_diagnosis = action.get("diagnosis")

            result        = env.step(action)
            total_reward += result.reward
            steps        += 1
            done          = result.done
            obs           = result.observation
            step_rewards.append(result.reward)

            print(f"[STEP] step={steps} action={json.dumps(action, separators=(',', ':'))} "
                  f"reward={result.reward:.2f} done={'true' if done else 'false'} error=null")

            if verbose:
                print(f"  reward={result.reward:+.4f}  cumulative={total_reward:+.4f}  "
                      f"done={done}  day={obs.day}  budget={obs.budget_remaining:.0f}")

            # Retrieve context for the next turn
            if rag_engine is not None and not done:
                try:
                    ctx = await rag_engine.retrieve(_build_rag_query(obs), k=RAG_K)
                    pending_rag = ctx.snippets or []
                    if verbose and pending_rag:
                        top = ctx.sources[0]["disease"] if ctx.sources else "-"
                        print(f"  [RAG] hits={ctx.meta.get('hits', 0)}  top={top}")
                except Exception as exc:
                    log.warning("RAG step %d failed: %s", steps, exc)
                    pending_rag = []

        state        = env.state()
        correct      = final_diagnosis == sc["hidden_diagnosis"]
        success      = correct
        budget_spent = sc["budget"] - state.budget_remaining

    finally:
        rewards_str = ",".join(f"{r:.2f}" for r in step_rewards)
        score = max(0.001, min(0.999, sum(step_rewards) / 10.0))
        print(f"[END] success={'true' if success else 'false'} steps={steps} score={score:.3f} rewards={rewards_str}")

    summary = {
        "scenario_id":  sc["id"],
        "diagnosis":    final_diagnosis,
        "hidden":       sc["hidden_diagnosis"],
        "correct":      correct,
        "total_reward": round(total_reward, 4),
        "steps":        steps,
        "referred":     state.referred,
        "budget_spent": budget_spent,
    }

    if verbose:
        print(f"\n{'─' * 62}\n  EPISODE SUMMARY\n{'─' * 62}")
        for k, v in summary.items():
            print(f"  {k:20s}: {v}")
        print()

    return summary


async def run_all(verbose: bool = False, rag_engine=None) -> None:
    results = []
    for sc in scenarios_v2:
        try:
            r = await run_episode(scenario=sc, verbose=verbose, rag_engine=rag_engine)
            results.append(r)
        except Exception as e:
            print(f"[ERROR] scenario {sc['id']} failed: {e}")
            return

    print(f"\n{'=' * 72}\n  BATCH RESULTS — {len(results)} scenarios\n{'=' * 72}")
    header = f"{'ID':10s} {'Difficulty':10s} {'Correct':8s} {'Reward':8s} {'Steps':6s} {'Referred':9s} {'Spent':6s}"
    print(f"\n  {header}\n  {'─' * 66}")
    for r in results:
        sc_obj = next(s for s in scenarios_v2 if s["id"] == r["scenario_id"])
        print(f"  {r['scenario_id']:10s} {sc_obj['difficulty_tier']:10s} "
              f"{'YES' if r['correct'] else 'NO':8s} {r['total_reward']:+8.3f} "
              f"{r['steps']:6d} {'YES' if r['referred'] else 'NO':9s} {r['budget_spent']:6.0f}")

    correct_count = sum(1 for r in results if r["correct"])
    avg_reward    = sum(r["total_reward"] for r in results) / len(results)
    print(f"\n  Correct: {correct_count}/{len(results)}  Avg reward: {avg_reward:+.3f}\n")


async def _init_rag_engine(force_disable: bool = False):
    if force_disable or os.environ.get("DISABLE_RAG") == "1":
        return None, None
    if not os.environ.get("SUPABASE_DB_URL"):
        return None, None
    try:
        from db.pool import get_pool
        from rag.engine_pg import PgRAGEngine
        from rag.embeddings import Embedder
        pool   = await get_pool()
        engine = PgRAGEngine(pool=pool, embedder=Embedder(), k=RAG_K)
        print(f"[INFO] RAG enabled: PgRAGEngine(k={RAG_K})")
        return engine, pool
    except Exception as exc:
        print(f"[WARN] RAG init failed ({exc}) — running without RAG")
        return None, None


def main():
    parser = argparse.ArgumentParser(description="RuralDoc LLM agent runner")
    parser.add_argument("--scenario", type=str, default=None)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--no-rag", action="store_true")
    args = parser.parse_args()
    asyncio.run(_async_main(args))


async def _async_main(args) -> None:
    from db.pool import close_pool
    rag_engine, _ = await _init_rag_engine(force_disable=args.no_rag)
    try:
        if args.all:
            await run_all(verbose=not args.quiet, rag_engine=rag_engine)
        elif args.scenario:
            sc = next((s for s in scenarios_v2 if s["id"] == args.scenario), None)
            if sc is None:
                print(f"[ERROR] Unknown scenario: {args.scenario}")
                return
            await run_episode(scenario=sc, verbose=not args.quiet, rag_engine=rag_engine)
        else:
            for sid in ("case_07", "case_10", "case_01"):
                sc = next((s for s in scenarios_v2 if s["id"] == sid), None)
                if sc:
                    await run_episode(scenario=sc, verbose=not args.quiet, rag_engine=rag_engine)
    finally:
        try:
            await close_pool()
        except Exception:
            pass


if __name__ == "__main__":
    main()
