"""
inference.py — Baseline LLM agent for MedicalDiagnosisEnv.

Reads configuration from environment variables:
    API_BASE_URL   — OpenAI-compatible base URL  (default: https://api.openai.com/v1)
    MODEL_NAME     — model to use                 (default: gpt-4o-mini)
    HF_TOKEN       — API key / HuggingFace token  (required)
    ENV_URL        — RuralDoc server URL          (default: http://localhost:8000)
    NUM_EPISODES   — how many episodes to run     (default: 3)
    MAX_STEPS      — max steps per episode        (default: 15)
    OUTPUT_FILE    — path for JSON log            (default: outputs/inference_log.json)

Log format (stdout):
    [START] episode=<n> scenario=<id>
    [STEP]  episode=<n> step=<k> action=<json> reward=<f> done=<bool>
    [END]   episode=<n> total_reward=<f> outcome=correct|wrong|budget|timeout

The JSON log is also saved to OUTPUT_FILE for offline analysis.
"""

from __future__ import annotations

import json
import os
import sys
import textwrap
import time
from pathlib import Path
from typing import Any

from openai import OpenAI

from client import RuralDocEnv


# ── Configuration from env ────────────────────────────────────────────────────

API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME   = os.getenv("MODEL_NAME",   "gpt-4o-mini")
HF_TOKEN     = os.getenv("HF_TOKEN",     os.getenv("OPENAI_API_KEY", ""))
ENV_URL      = os.getenv("ENV_URL",      "http://localhost:8000")
NUM_EPISODES = int(os.getenv("NUM_EPISODES", "3"))
MAX_STEPS    = int(os.getenv("MAX_STEPS",    "15"))
OUTPUT_FILE  = os.getenv("OUTPUT_FILE",  "outputs/inference_log.json")


# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = textwrap.dedent("""\
    You are a rural Indian doctor working at a Primary Health Centre (PHC).
    You have limited diagnostic resources and a tight budget.
    Your job is to reach the correct diagnosis as quickly and cheaply as possible.

    On each turn you receive a JSON observation describing:
      - patient demographics (age, gender, location)
      - current symptoms and vital signs
      - available diagnostic tests and their costs
      - your remaining budget
      - your memory of test results so far
      - the patient's current status (stable / worsening / critical)

    You MUST respond with exactly one JSON action in one of these forms:
      {"type": "order_test", "test_name": "<name>"}
      {"type": "diagnose",   "diagnosis": "<name>"}
      {"type": "refer"}

    Rules:
    - Only order tests that are in available_tests and you can afford.
    - Do not repeat a test you have already ordered.
    - If the scenario requires referral and you are confident, refer BEFORE diagnosing.
    - Diagnose as soon as you are confident — do not waste budget on extra tests.
    - Output ONLY valid JSON and nothing else.
""")


# ── Prompt helpers ────────────────────────────────────────────────────────────

def obs_to_prompt(obs: dict, step: int, tests_ordered: list[str]) -> str:
    """Convert an observation dict into a human-readable prompt for the LLM."""
    vitals = obs.get("vitals", {})
    available = [
        t for t in obs.get("available_tests", [])
        if t not in tests_ordered
    ]
    memory = obs.get("memory", [])

    lines = [
        f"=== Day {obs['day']} | Step {step} ===",
        f"Patient: {obs['patient'].get('age')}y {obs['patient'].get('gender')}, "
        f"{obs['patient'].get('location')}",
        f"Status: {obs['status'].upper()}",
        f"Budget remaining: {obs['budget_remaining']:.1f}",
        "",
        "Symptoms: " + ", ".join(obs.get("symptoms", [])),
        "Vitals:   " + "  ".join(f"{k}={v}" for k, v in vitals.items()),
        "",
    ]

    if memory:
        lines.append("Test results so far:")
        for note in memory:
            lines.append(f"  • {note}")
        lines.append("")

    if available:
        lines.append(f"Available tests (not yet ordered): {', '.join(available)}")
    else:
        lines.append("No new tests available.")

    lines.append("")
    lines.append("Respond with exactly one JSON action.")
    return "\n".join(lines)


def parse_action(content: str) -> dict | None:
    """
    Extract a JSON action dict from the LLM's response text.
    Returns None if parsing fails.
    """
    content = content.strip()
    # Strip markdown code fences if present
    if content.startswith("```"):
        lines = content.splitlines()
        content = "\n".join(
            l for l in lines if not l.startswith("```")
        ).strip()
    try:
        data = json.loads(content)
        if isinstance(data, dict) and "type" in data:
            return data
    except json.JSONDecodeError:
        pass
    return None


# ── Episode runner ────────────────────────────────────────────────────────────

def run_episode(
    env: RuralDocEnv,
    llm: OpenAI,
    episode_num: int,
    scenario_id: str | None = None,
) -> dict[str, Any]:
    """
    Run one full episode.  Returns a log dict with all steps.
    """
    obs = env.reset(scenario_id=scenario_id)
    state = env.state()

    print(f"[START] episode={episode_num} scenario={state['scenario_id']}")

    history: list[dict] = []          # LLM message history
    step_logs: list[dict] = []
    tests_ordered: list[str] = []
    total_reward = 0.0
    outcome = "timeout"

    for step in range(1, MAX_STEPS + 1):
        # Build user message
        user_msg = obs_to_prompt(obs, step, tests_ordered)
        history.append({"role": "user", "content": user_msg})

        # Call LLM
        try:
            response = llm.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "system", "content": SYSTEM_PROMPT}] + history,
                temperature=0.2,
                max_tokens=128,
            )
            assistant_text = response.choices[0].message.content or ""
        except Exception as exc:
            print(f"  LLM error at step {step}: {exc}", file=sys.stderr)
            break

        history.append({"role": "assistant", "content": assistant_text})

        # Parse action
        action = parse_action(assistant_text)
        if action is None:
            print(f"  Could not parse action from: {assistant_text!r}", file=sys.stderr)
            # Force a diagnose with unknown to end episode gracefully
            action = {"type": "diagnose", "diagnosis": "unknown"}

        # Step environment
        result = env.step(action)
        obs = result["observation"]
        reward = result["reward"]
        done = result["done"]
        total_reward += reward

        # Track tests ordered
        if action["type"] == "order_test":
            tests_ordered.append(action.get("test_name", ""))

        step_log = {
            "step":   step,
            "action": action,
            "reward": reward,
            "done":   done,
        }
        step_logs.append(step_log)

        print(
            f"[STEP]  episode={episode_num} step={step} "
            f"action={json.dumps(action)} reward={reward:.4f} done={done}"
        )

        if done:
            if action["type"] == "diagnose":
                # Check if it was correct by looking at reward signal
                # +1.0 base for correct — any positive diagnose reward implies correct
                outcome = "correct" if reward > 0 else "wrong"
            elif result["observation"]["budget_remaining"] <= 0:
                outcome = "budget"
            else:
                outcome = "critical"
            break

    print(
        f"[END]   episode={episode_num} total_reward={total_reward:.4f} "
        f"outcome={outcome}"
    )

    return {
        "episode":       episode_num,
        "scenario_id":   state["scenario_id"],
        "total_reward":  total_reward,
        "outcome":       outcome,
        "steps":         step_logs,
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    if not HF_TOKEN:
        print(
            "Error: HF_TOKEN (or OPENAI_API_KEY) environment variable not set.",
            file=sys.stderr,
        )
        sys.exit(1)

    llm = OpenAI(api_key=HF_TOKEN, base_url=API_BASE_URL)

    all_logs: list[dict] = []

    with RuralDocEnv(base_url=ENV_URL) as env:
        # Verify server is up
        try:
            env.health()
        except Exception as exc:
            print(f"Cannot reach server at {ENV_URL}: {exc}", file=sys.stderr)
            sys.exit(1)

        scenarios = env.scenarios()
        scenario_ids = [s["id"] for s in scenarios]

        for ep in range(1, NUM_EPISODES + 1):
            # Cycle through scenarios deterministically
            sid = scenario_ids[(ep - 1) % len(scenario_ids)]
            log = run_episode(env, llm, episode_num=ep, scenario_id=sid)
            all_logs.append(log)
            time.sleep(0.5)  # brief pause between episodes

    # Save JSON log
    out_path = Path(OUTPUT_FILE)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_logs, f, indent=2)

    print(f"\nInference log saved to {out_path}")

    # Summary
    correct = sum(1 for l in all_logs if l["outcome"] == "correct")
    avg_reward = sum(l["total_reward"] for l in all_logs) / len(all_logs)
    print(f"Summary: {correct}/{NUM_EPISODES} correct  avg_reward={avg_reward:.4f}")


if __name__ == "__main__":
    main()
