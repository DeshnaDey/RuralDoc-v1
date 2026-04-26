"""
env/train_grpo.py — GRPO training for the RuralDoc medical diagnosis agent.

What this is
    A custom GRPO (Group Relative Policy Optimization) loop wired to
    `MedicalDiagnosisEnvironment`. Each training step:

        1. Pick N scenarios from scenarios_v2.
        2. For each scenario, roll out G episodes with the current policy.
           A "rollout" is a multi-turn interaction with env.step(); on every
           turn the model generates a JSON action, the env returns reward,
           and we record (prompt_ids, action_ids, sampling-time log_probs).
        3. Score each episode with `calculate_episode_score` (rewards.py).
        4. Compute group-relative advantage:
               A_i = (score_i - mean(group)) / (std(group) + eps)
           Every turn in the same episode shares its episode's advantage —
           equivalent to broadcasting the terminal reward over all timesteps,
           which is the standard GRPO simplification (no value head, no GAE).
        5. PPO-style clipped surrogate update.

Why custom (not trl.GRPOTrainer)
    TRL's GRPOTrainer expects single-turn `(prompt, completion)` pairs and
    samples G completions via its internal generate(). Our completion is
    multi-turn — each agent decision is a fresh call with a different prompt.
    We use the same advantage math TRL uses, but the rollout loop is ours.

Defaults
    --model defaults to Qwen/Qwen2.5-0.5B-Instruct (fits on laptop CPU/MPS).
    The HF inference model from your .env (Llama-3.1-8B-Instruct) is for
    serving, not training — you can't update weights you don't host.

Usage
    # Smoke run for blog/demo screenshot (~50 steps, fast)
    python -m env.train_grpo --smoke

    # Full run
    python -m env.train_grpo --steps 1000 --group-size 8 --scenarios-per-step 4

Outputs (under --out-dir, default outputs/grpo/)
    reward_curve.png       — the screenshot
    reward_history.json    — raw mean-score per step
    final/                 — saved model + tokenizer
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from dataclasses import dataclass
from pathlib import Path

# Make `env.*` importable when running as a script
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import torch
import torch.nn.functional as F
from torch.optim import AdamW

# Lazy import for matplotlib so an import-time failure doesn't kill training
try:
    import matplotlib

    matplotlib.use("Agg")  # headless save; no display required
    import matplotlib.pyplot as plt
except Exception:  # pragma: no cover
    plt = None  # type: ignore

from transformers import AutoModelForCausalLM, AutoTokenizer

from env.environment import MedicalDiagnosisEnvironment
from env.rewards import calculate_episode_score
from env.scenarios import scenarios_v2
from env.inference import SYSTEM_PROMPT, render_observation, parse_action


# ─────────────────────────────────────────────────────────────────────────────
#  Records
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class TurnRecord:
    """One agent turn captured during rollout."""

    prompt_ids: torch.Tensor   # (T_p,)  long
    action_ids: torch.Tensor   # (T_a,)  long
    sampling_logprob: torch.Tensor   # scalar — sum log_pi_old(a|s) at sampling time


@dataclass
class EpisodeRecord:
    turns: list[TurnRecord]
    score: float          # calculate_episode_score in [0.001, 0.999]
    step_rewards: list[float]
    correct: bool
    final_diagnosis: str | None


# ─────────────────────────────────────────────────────────────────────────────
#  Rollout — multi-turn agent loop with logprob capture
# ─────────────────────────────────────────────────────────────────────────────


@torch.no_grad()
def rollout_episode(
    model,
    tokenizer,
    scenario: dict,
    device: torch.device,
    max_new_tokens: int = 64,
    temperature: float = 1.0,
    top_p: float = 0.95,
) -> EpisodeRecord:
    """
    Run one full episode, capturing per-turn (prompt, action, sampling logprob).
    The episode's terminal score is computed via calculate_episode_score.
    """
    env = MedicalDiagnosisEnvironment()
    obs = env.reset(scenario=scenario)
    sc = env._scenario

    conversation: list[dict] = []
    turns: list[TurnRecord] = []
    step_rewards: list[float] = []
    final_diagnosis: str | None = None
    max_steps = sc["critical_window_days"] * 2 + 5
    steps = 0
    done = False

    while not done and steps < max_steps:
        # 1. Build the prompt for this turn
        user_text = render_observation(obs, sc["test_costs"])
        conversation.append({"role": "user", "content": user_text})
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + conversation
        prompt_ids = tokenizer.apply_chat_template(
            messages,
            return_tensors="pt",
            add_generation_prompt=True,
        ).to(device)

        # 2. Sample an action and capture per-token logprobs
        out = model.generate(
            prompt_ids,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            temperature=temperature,
            top_p=top_p,
            return_dict_in_generate=True,
            output_scores=True,
            pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
        )
        action_ids = out.sequences[0, prompt_ids.shape[1]:]
        # out.scores is a tuple of length T_a; each entry is (1, V) pre-softmax logits
        logprobs_per_token = []
        for t, score_t in enumerate(out.scores):
            log_softmax_t = torch.log_softmax(score_t[0], dim=-1)
            tok_id = action_ids[t]
            logprobs_per_token.append(log_softmax_t[tok_id])
        sampling_logprob = (
            torch.stack(logprobs_per_token).sum().detach().cpu()
            if logprobs_per_token
            else torch.tensor(0.0)
        )

        # 3. Decode the action and feed it to the env
        action_text = tokenizer.decode(action_ids, skip_special_tokens=True)
        action = parse_action(action_text) or {"type": "diagnose", "diagnosis": "unknown"}

        turns.append(
            TurnRecord(
                prompt_ids=prompt_ids[0].cpu(),
                action_ids=action_ids.cpu(),
                sampling_logprob=sampling_logprob,
            )
        )
        conversation.append({"role": "assistant", "content": action_text})

        if action["type"] == "diagnose":
            final_diagnosis = action.get("diagnosis")

        result = env.step(action)
        step_rewards.append(result.reward)
        obs = result.observation
        done = result.done
        steps += 1

    score = calculate_episode_score(
        episode_rewards=step_rewards,
        final_diagnosis=final_diagnosis or "unknown",
        scenario=sc,
        referred=env.state().referred,
    )
    return EpisodeRecord(
        turns=turns,
        score=score,
        step_rewards=step_rewards,
        correct=(final_diagnosis == sc["hidden_diagnosis"]),
        final_diagnosis=final_diagnosis,
    )


# ─────────────────────────────────────────────────────────────────────────────
#  GRPO update — group-relative advantage + clipped surrogate loss
# ─────────────────────────────────────────────────────────────────────────────


def grpo_loss(
    model,
    groups: list[list[EpisodeRecord]],
    device: torch.device,
    clip_eps: float = 0.2,
    micro_batch: int = 8,
) -> tuple[torch.Tensor, dict]:
    """
    Compute the GRPO-clipped surrogate loss across all turns in all groups.

    Per group of G episodes:
        advantage_i = (score_i - mean) / (std + eps)        (i = 1..G)
    Each turn in episode i inherits its episode's advantage. Per turn:
        ratio  = exp(new_logprob - sampling_logprob)
        surrogate_t = -min(ratio * adv, clip(ratio, 1±eps) * adv)
    """
    losses: list[torch.Tensor] = []
    metric_ratios: list[float] = []
    metric_clipped = 0
    metric_total = 0

    eps_std = 1e-6

    # Flatten into (turn, advantage) tuples first so we can micro-batch.
    flat: list[tuple[TurnRecord, float]] = []
    for group in groups:
        scores = torch.tensor([ep.score for ep in group])
        if scores.std() < eps_std:
            # Degenerate group — no signal. Skip.
            continue
        advantages = (scores - scores.mean()) / (scores.std() + eps_std)
        for ep, adv in zip(group, advantages):
            for turn in ep.turns:
                flat.append((turn, adv.item()))

    if not flat:
        return torch.tensor(0.0, device=device, requires_grad=True), {
            "n_turns": 0,
            "frac_clipped": 0.0,
        }

    # Forward each turn one at a time (variable seq lens; batching across turns
    # would need padding/masking — keep it simple for the smoke test).
    for turn, advantage in flat:
        prompt_ids = turn.prompt_ids.unsqueeze(0).to(device)            # (1, T_p)
        action_ids = turn.action_ids.unsqueeze(0).to(device)            # (1, T_a)
        full_ids = torch.cat([prompt_ids, action_ids], dim=1)           # (1, T_p+T_a)

        logits = model(full_ids).logits  # (1, T, V)
        # Logits at position t predict token at position t+1.
        # We want to score action_ids[:, 0..T_a-1] given prefix [prompt + action[:t]].
        # The relevant logit indices are [T_p - 1 .. T_p + T_a - 2].
        T_p = prompt_ids.shape[1]
        T_a = action_ids.shape[1]
        action_logits = logits[0, T_p - 1 : T_p - 1 + T_a]              # (T_a, V)
        log_probs = torch.log_softmax(action_logits, dim=-1)
        tok_logprobs = log_probs.gather(1, action_ids[0].unsqueeze(1)).squeeze(1)  # (T_a,)
        new_logprob = tok_logprobs.sum()

        ratio = torch.exp(new_logprob - turn.sampling_logprob.to(device))
        clipped = torch.clamp(ratio, 1 - clip_eps, 1 + clip_eps)
        surrogate = -torch.min(ratio * advantage, clipped * advantage)
        losses.append(surrogate)

        metric_ratios.append(ratio.item())
        if (advantage > 0 and ratio.item() > 1 + clip_eps) or (
            advantage < 0 and ratio.item() < 1 - clip_eps
        ):
            metric_clipped += 1
        metric_total += 1

    loss = torch.stack(losses).mean()
    metrics = {
        "n_turns": metric_total,
        "frac_clipped": metric_clipped / max(metric_total, 1),
        "mean_ratio": sum(metric_ratios) / max(len(metric_ratios), 1),
    }
    return loss, metrics


# ─────────────────────────────────────────────────────────────────────────────
#  Reward-curve plotting
# ─────────────────────────────────────────────────────────────────────────────


def plot_reward_curve(history: list[float], path: Path) -> None:
    if plt is None:
        return
    fig, ax = plt.subplots(figsize=(9, 5))
    steps = list(range(1, len(history) + 1))
    ax.plot(steps, history, marker="o", linewidth=1.2, markersize=3,
            alpha=0.55, label="step mean")
    if len(history) >= 5:
        window = 5
        avg = []
        for i in range(len(history)):
            lo = max(0, i - window + 1)
            avg.append(sum(history[lo:i + 1]) / (i + 1 - lo))
        ax.plot(steps, avg, linewidth=2.5, label=f"trailing-{window} mean")
    ax.set_xlabel("training step")
    ax.set_ylabel("mean episode score (calculate_episode_score)")
    ax.set_title("RuralDoc — GRPO reward curve")
    ax.set_ylim(0.0, 1.0)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


# ─────────────────────────────────────────────────────────────────────────────
#  Main loop
# ─────────────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="GRPO trainer for RuralDoc agent.")
    parser.add_argument("--model", default="Qwen/Qwen2.5-0.5B-Instruct",
                        help="HF model id. Default: Qwen2.5-0.5B (laptop-friendly).")
    parser.add_argument("--smoke", action="store_true",
                        help="Tiny config: 50 steps, group=4, 2 scenarios/step.")
    parser.add_argument("--steps", type=int, default=200)
    parser.add_argument("--group-size", type=int, default=4)
    parser.add_argument("--scenarios-per-step", type=int, default=2)
    parser.add_argument("--lr", type=float, default=1e-6)
    parser.add_argument("--clip-eps", type=float, default=0.2)
    parser.add_argument("--max-new-tokens", type=int, default=64)
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--top-p", type=float, default=0.95)
    parser.add_argument("--device", default=None,
                        help="auto-detects mps/cuda/cpu if unset")
    parser.add_argument("--out-dir", default="outputs/grpo")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if args.smoke:
        args.steps = 50
        args.group_size = 4
        args.scenarios_per_step = 2

    random.seed(args.seed)
    torch.manual_seed(args.seed)

    if args.device:
        device = torch.device(args.device)
    elif torch.cuda.is_available():
        device = torch.device("cuda")
    elif torch.backends.mps.is_available():
        device = torch.device("mps")
    else:
        device = torch.device("cpu")
    print(f"[INFO] device={device} model={args.model}")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] loading tokenizer + model …")
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(args.model, torch_dtype=torch.float32)
    model = model.to(device)
    optimizer = AdamW(model.parameters(), lr=args.lr)

    pool = scenarios_v2[:5] if args.smoke else scenarios_v2
    print(f"[INFO] scenario pool size = {len(pool)}")
    print(
        f"[INFO] starting GRPO: steps={args.steps} group={args.group_size} "
        f"scenarios/step={args.scenarios_per_step} lr={args.lr}"
    )

    reward_history: list[float] = []
    correct_history: list[float] = []

    for step in range(args.steps):
        groups: list[list[EpisodeRecord]] = []
        scenarios_this = random.sample(
            pool, k=min(args.scenarios_per_step, len(pool))
        )

        # ── Rollout (model in eval; no grads) ────────────────────────────────
        model.eval()
        for sc in scenarios_this:
            group = [
                rollout_episode(
                    model, tokenizer, sc, device,
                    max_new_tokens=args.max_new_tokens,
                    temperature=args.temperature,
                    top_p=args.top_p,
                )
                for _ in range(args.group_size)
            ]
            groups.append(group)

        # ── GRPO update ──────────────────────────────────────────────────────
        model.train()
        loss, metrics = grpo_loss(model, groups, device, clip_eps=args.clip_eps)
        if metrics["n_turns"] > 0:
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            loss_val = loss.item()
        else:
            loss_val = float("nan")

        all_eps = [ep for grp in groups for ep in grp]
        mean_score = sum(ep.score for ep in all_eps) / len(all_eps)
        frac_correct = sum(ep.correct for ep in all_eps) / len(all_eps)
        reward_history.append(mean_score)
        correct_history.append(frac_correct)

        print(
            f"[step {step + 1:4d}/{args.steps}]  "
            f"score={mean_score:.3f}  correct={frac_correct:.2f}  "
            f"loss={loss_val:+.4f}  turns={metrics['n_turns']}  "
            f"clipped={metrics.get('frac_clipped', 0.0):.2f}"
        )

        # Periodic checkpoint of the curve so screenshotting can happen mid-run
        if (step + 1) % 5 == 0 or step == args.steps - 1:
            plot_reward_curve(reward_history, out_dir / "reward_curve.png")

    # Final artifacts
    print(f"\n[DONE] saving to {out_dir}/")
    final_dir = out_dir / "final"
    final_dir.mkdir(exist_ok=True)
    model.save_pretrained(final_dir)
    tokenizer.save_pretrained(final_dir)
    plot_reward_curve(reward_history, out_dir / "reward_curve.png")

    with open(out_dir / "reward_history.json", "w") as f:
        json.dump(
            {
                "model": args.model,
                "steps": args.steps,
                "group_size": args.group_size,
                "scenarios_per_step": args.scenarios_per_step,
                "lr": args.lr,
                "reward": reward_history,
                "correct": correct_history,
            },
            f,
            indent=2,
        )

    print(f"       reward_curve.png  → screenshot for blog post")
    print(f"       final/            → trained model checkpoint")
    print(f"       reward_history.json → raw scores per step")


if __name__ == "__main__":
    main()
