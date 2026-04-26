"""
scripts/train_grpo.py — GRPO training for RuralDoc agent.

Run on Google Colab with A100/T4 GPU:
    pip install trl transformers datasets accelerate peft bitsandbytes openai
    python scripts/train_grpo.py

Environment variables required:
    HF_TOKEN       — HuggingFace token for model access + pushing
    API_BASE_URL   — inference endpoint for reward scoring
    SUPABASE_DB_URL — optional, for RAG
"""

import os
import json
import asyncio
import re
from typing import Any

import torch
from datasets import Dataset
from transformers import AutoTokenizer, AutoModelForCausalLM
from trl import GRPOConfig, GRPOTrainer
from openai import AsyncOpenAI

# ── Config ────────────────────────────────────────────────────────────────────
MODEL_NAME   = os.environ.get("MODEL_NAME", "meta-llama/Llama-3.1-8B-Instruct")
HF_TOKEN     = os.environ.get("HF_TOKEN", "")
OUTPUT_DIR   = os.environ.get("OUTPUT_DIR", "./ruraldoc-grpo")
MAX_STEPS    = int(os.environ.get("MAX_STEPS", "200"))
BATCH_SIZE   = int(os.environ.get("BATCH_SIZE", "4"))
LR           = float(os.environ.get("LR", "5e-6"))

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from env.scenarios import scenarios_v2

TRAIN_SCENARIOS = scenarios_v2[:20]  # use first 20 for training

SYSTEM_PROMPT = """You are RuralDoc — an AI clinical decision-support agent for rural Indian PHCs.
Diagnose patients using only basic PHC tools on a limited budget.

Available action types:
1. Order a test: {"type": "order_test", "test_name": "<name>"}
2. Make diagnosis: {"type": "diagnose", "diagnosis": "<disease_name>"}
3. Refer patient: {"type": "refer", "reason": "<reason>"}

Always respond with a single valid JSON object. Be efficient — budget is limited."""


def scenario_to_prompt(scenario: dict) -> str:
    p = scenario.get("patient", {})
    symptoms = "\n".join(f"  • {s}" for s in scenario.get("presenting_symptoms", []))
    vitals = scenario.get("vitals", {})
    tests = "\n".join(
        f"  • {name} [{cost} units]"
        for name, cost in scenario.get("test_costs", {}).items()
    )
    return f"""PATIENT
  Age: {p.get('age', '?')}  Gender: {p.get('gender', '?')}  Location: {p.get('location', '?')}
SYMPTOMS
{symptoms}
VITALS
  Temp: {vitals.get('temperature', '?')}  BP: {vitals.get('bp', '?')}  HR: {vitals.get('hr', '?')}  SpO2: {vitals.get('spo2', '?')}
BUDGET: {scenario.get('budget', 20)} units
AVAILABLE TESTS
{tests}

Respond with a single JSON action object."""


def compute_reward(response: str, scenario: dict, step: int = 1) -> float:
    from env.rewards import calculate_reward
    try:
        match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
        if not match:
            return -0.15
        action = json.loads(match.group())
    except json.JSONDecodeError:
        return -0.15

    current_state = {
        "current_day": 1,
        "budget_remaining": scenario.get("budget", 20),
        "tests_ordered": [],
        "referred": False,
    }
    try:
        return calculate_reward(current_state, action, scenario)
    except Exception:
        return -0.05


def build_dataset() -> Dataset:
    data = []
    for _ in range(10):
        for sc in TRAIN_SCENARIOS:
            prompt = scenario_to_prompt(sc)
            data.append({
                "prompt": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "scenario_id": sc["id"],
            })
    return Dataset.from_list(data)


def make_reward_fn(scenarios_map: dict):
    """Return a reward function compatible with TRL GRPOTrainer."""
    def reward_fn(completions, prompts=None, **kwargs) -> list[float]:
        rewards = []
        scenario_ids = kwargs.get("scenario_id", [])
        for i, completion in enumerate(completions):
            # Get the text from completion
            if isinstance(completion, list):
                text = completion[0].get("content", "") if completion else ""
            else:
                text = str(completion)

            sc_id = scenario_ids[i] if i < len(scenario_ids) else TRAIN_SCENARIOS[0]["id"]
            sc = scenarios_map.get(sc_id, TRAIN_SCENARIOS[0])
            r = compute_reward(text, sc)
            rewards.append(r)
        return rewards
    return reward_fn


def main():
    print(f"[INFO] Loading model: {MODEL_NAME}")
    print(f"[INFO] Output dir: {OUTPUT_DIR}")
    print(f"[INFO] Max steps: {MAX_STEPS}")

    # Build dataset
    dataset = build_dataset()
    scenarios_map = {sc["id"]: sc for sc in TRAIN_SCENARIOS}
    print(f"[INFO] Dataset size: {len(dataset)}")

    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_NAME,
        token=HF_TOKEN,
        padding_side="left",
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # GRPO config
    config = GRPOConfig(
        output_dir=OUTPUT_DIR,
        num_train_epochs=1,
        max_steps=MAX_STEPS,
        per_device_train_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=4,
        learning_rate=LR,
        logging_steps=10,
        save_steps=50,
        warmup_steps=20,
        bf16=torch.cuda.is_available(),
        remove_unused_columns=False,
        report_to="none",
        max_completion_length=256,
        num_generations=4,
        temperature=0.8,
        push_to_hub=bool(HF_TOKEN),
        hub_model_id=f"Kiddy007/ruraldoc-grpo" if HF_TOKEN else None,
        hub_token=HF_TOKEN or None,
    )

    # Load model
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        token=HF_TOKEN,
        torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
        device_map="auto",
    )

    # Reward function
    reward_fn = make_reward_fn(scenarios_map)

    # Trainer
    trainer = GRPOTrainer(
        model=model,
        args=config,
        train_dataset=dataset,
        reward_funcs=reward_fn,
        processing_class=tokenizer,
    )

    print("[INFO] Starting GRPO training...")
    trainer.train()
    print("[INFO] Training complete!")

    # Save
    trainer.save_model(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    print(f"[INFO] Model saved to {OUTPUT_DIR}")

    if HF_TOKEN:
        print("[INFO] Pushing to HuggingFace Hub...")
        trainer.push_to_hub()


if __name__ == "__main__":
    main()
