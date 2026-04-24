"""
dev/perf_test.py — end-to-end smoke + performance check.

Runs N episodes (default 10) of MedicalDiagnosisEnvironment using a simple
"informed random" policy that mostly picks cheap first-line tests, occasionally
the scenario's conclusive test, an early referral if required, and finally a
diagnose action. Every episode is persisted to Supabase via env.persist().

Measures:
  • per-step latency (sync env.step)
  • per-episode persist latency (async env.persist)
  • end-to-end total time, per-episode wall time
  • outcome distribution
  • cumulative reward

Writes a JSON report to dev/runs/ and prints a summary.

Run (from repo root):
    python dev/perf_test.py --n 10 --agent-version random_v0
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from env.environment import MedicalDiagnosisEnvironment
from env.scenarios import scenarios_v2
from db.pool import close_pool, get_conn


# ── Policy ───────────────────────────────────────────────────────────────────

def informed_random_policy(obs, scenario: dict, tests_ordered: list[str], referred: bool, step_idx: int):
    """
    Shallow heuristic policy — not meant to be good, just to exercise every
    branch of the reward function and produce varied episode traces.

    Rough script:
      step 1:  refer (if scenario requires it) else cheap screening test
      step 2:  cheap relevant test (thermometer / auscultation)
      step 3:  conclusive test
      step 4+: diagnose with the scenario's hidden_diagnosis most of the time,
               otherwise a near-miss from suggests list.
    """
    relevant = scenario.get("relevant_tests", [])
    conclusive = scenario.get("conclusive_test")
    requires_referral = scenario.get("requires_referral", False)

    # Step-based script
    if step_idx == 0 and requires_referral and not referred:
        return {"type": "refer"}

    if step_idx <= 1:
        # cheap first-line test
        cheap = [t for t in relevant if t not in tests_ordered]
        if cheap:
            return {"type": "order_test", "test_name": random.choice(cheap)}

    if step_idx == 2 and conclusive and conclusive not in tests_ordered:
        return {"type": "order_test", "test_name": conclusive}

    # After that, 80% diagnose correctly, 20% diagnose wrong
    if random.random() < 0.8:
        return {"type": "diagnose", "diagnosis": scenario["hidden_diagnosis"]}
    wrong_candidates = [s["hidden_diagnosis"] for s in scenarios_v2 if s["hidden_diagnosis"] != scenario["hidden_diagnosis"]]
    return {"type": "diagnose", "diagnosis": random.choice(wrong_candidates)}


# ── Runner ───────────────────────────────────────────────────────────────────

async def run_one_episode(scenario: dict, agent_version: str) -> dict:
    env = MedicalDiagnosisEnvironment(agent_version=agent_version)
    obs = env.reset(scenario=scenario)

    step_latencies_ms: list[float] = []
    episode_start = time.perf_counter()

    done = False
    step_idx = 0
    cumulative = 0.0
    last_action_type = None
    while not done and step_idx < 20:  # hard cap to avoid runaway
        action = informed_random_policy(
            obs,
            scenario,
            env._tests_ordered,
            env._referred,
            step_idx,
        )
        t0 = time.perf_counter()
        result = env.step(action)
        step_latencies_ms.append((time.perf_counter() - t0) * 1000.0)
        cumulative += result.reward
        obs = result.observation
        done = result.done
        last_action_type = action["type"]
        step_idx += 1

    rollout_ms = (time.perf_counter() - episode_start) * 1000.0

    # Persist
    persist_start = time.perf_counter()
    ok = await env.persist()
    persist_ms = (time.perf_counter() - persist_start) * 1000.0

    return {
        "scenario_id": scenario["id"],
        "hidden_diagnosis": scenario["hidden_diagnosis"],
        "steps": step_idx,
        "outcome": env._outcome,
        "referred": env._referred,
        "final_diagnosis": env._final_diagnosis,
        "cumulative_reward": round(cumulative, 4),
        "persisted": ok,
        "rollout_ms": round(rollout_ms, 3),
        "persist_ms": round(persist_ms, 3),
        "step_latencies_ms": [round(x, 4) for x in step_latencies_ms],
    }


async def main(n: int, agent_version: str, seed: int | None) -> int:
    if seed is not None:
        random.seed(seed)

    # Pre-flight: check the active knowledge_version has scenarios seeded.
    try:
        async with get_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM public.scenarios s
                    JOIN public.knowledge_versions kv ON kv.id = s.knowledge_version_id
                    WHERE kv.is_active;
                    """
                )
                row = await cur.fetchone()
                scenario_count = row[0] if row else 0
    except Exception as e:
        print(f"[perf_test] pre-flight DB check FAILED: {e}")
        return 1

    if scenario_count == 0:
        print("[perf_test] ABORT: no scenarios under the active knowledge_version.")
        print("  run: python scripts/seed_knowledge.py && python scripts/seed_scenarios.py")
        return 2
    print(f"[perf_test] active knowledge_version has {scenario_count} scenarios seeded.")
    print(f"[perf_test] running {n} episodes (agent_version={agent_version!r})...")

    total_start = time.perf_counter()
    episodes = []
    for i in range(n):
        scenario = random.choice(scenarios_v2)
        ep = await run_one_episode(scenario, agent_version)
        episodes.append(ep)
        print(
            f"  ep {i+1:>2d}/{n}  scenario={ep['scenario_id']:<8s} "
            f"steps={ep['steps']:<2d} outcome={ep['outcome']:<18s} "
            f"reward={ep['cumulative_reward']:+.3f} "
            f"rollout={ep['rollout_ms']:6.1f}ms  persist={ep['persist_ms']:6.1f}ms"
            f"  {'✓' if ep['persisted'] else '✗'}"
        )
    total_ms = (time.perf_counter() - total_start) * 1000.0

    # ── Aggregate stats ──
    all_step_latencies = [x for ep in episodes for x in ep["step_latencies_ms"]]
    persist_latencies = [ep["persist_ms"] for ep in episodes]
    rollout_latencies = [ep["rollout_ms"] for ep in episodes]
    outcomes = {}
    for ep in episodes:
        outcomes[ep["outcome"]] = outcomes.get(ep["outcome"], 0) + 1
    persisted_ok = sum(1 for ep in episodes if ep["persisted"])

    def stat(values: list[float]) -> dict:
        if not values:
            return {"n": 0}
        s = sorted(values)

        def pct(p: float) -> float:
            if not s:
                return 0.0
            k = int(round((p / 100.0) * (len(s) - 1)))
            return s[k]

        return {
            "n": len(values),
            "mean": round(statistics.mean(values), 3),
            "median": round(statistics.median(values), 3),
            "p95": round(pct(95), 3),
            "p99": round(pct(99), 3),
            "max": round(max(values), 3),
        }

    report = {
        "meta": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "n_episodes": n,
            "agent_version": agent_version,
            "seed": seed,
            "total_elapsed_ms": round(total_ms, 2),
            "throughput_eps_per_sec": round(n / (total_ms / 1000.0), 3) if total_ms > 0 else 0.0,
        },
        "outcomes": outcomes,
        "persist_success_rate": persisted_ok / n if n else 0.0,
        "rewards": {
            "mean": round(statistics.mean(ep["cumulative_reward"] for ep in episodes), 4),
            "min": min(ep["cumulative_reward"] for ep in episodes),
            "max": max(ep["cumulative_reward"] for ep in episodes),
        },
        "step_latency_ms": stat(all_step_latencies),
        "rollout_latency_ms": stat(rollout_latencies),
        "persist_latency_ms": stat(persist_latencies),
        "episodes": episodes,
    }

    # ── Write report ──
    runs_dir = Path(__file__).resolve().parent / "runs"
    runs_dir.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path = runs_dir / f"perf_{stamp}.json"
    report_path.write_text(json.dumps(report, indent=2, default=str))

    # ── Print summary ──
    print("\n" + "=" * 62)
    print("  perf summary")
    print("=" * 62)
    print(f"  episodes           : {n}")
    print(f"  total elapsed      : {total_ms:.1f} ms")
    print(f"  throughput         : {report['meta']['throughput_eps_per_sec']} eps/sec")
    print(f"  persist success    : {persisted_ok}/{n}")
    print(f"  outcomes           : {outcomes}")
    print(f"  mean reward        : {report['rewards']['mean']:+.3f}")
    print(f"  step latency (ms)  : mean={report['step_latency_ms']['mean']}  p95={report['step_latency_ms']['p95']}  max={report['step_latency_ms']['max']}")
    print(f"  persist latency(ms): mean={report['persist_latency_ms']['mean']}  p95={report['persist_latency_ms']['p95']}  max={report['persist_latency_ms']['max']}")
    print(f"  report             : {report_path}")

    # ── DB row-count snapshot post-run ──
    print("\n  post-run row counts under active knowledge_version:")
    try:
        async with get_conn() as conn:
            async with conn.cursor() as cur:
                for t in ["episodes", "episode_steps"]:
                    await cur.execute(f"SELECT COUNT(*) FROM public.{t};")
                    row = await cur.fetchone()
                    print(f"    {t:16s} {row[0]}")
    except Exception as e:
        print(f"    [row-count check failed: {e}]")

    await close_pool()
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10, help="number of episodes (default 10)")
    ap.add_argument("--agent-version", default="random_v0", help="tag for episode rows")
    ap.add_argument("--seed", type=int, default=None, help="RNG seed for reproducibility")
    args = ap.parse_args()

    sys.exit(asyncio.run(main(args.n, args.agent_version, args.seed)))
