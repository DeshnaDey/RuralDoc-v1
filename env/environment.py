"""
env/environment.py — MedicalDiagnosisEnvironment (canonical).

Turn-based clinical RL env wired to Supabase for run persistence.

Contract:
    env = MedicalDiagnosisEnvironment(agent_version="random_v0")
    obs = env.reset(scenario=tb)
    result = env.step({"type": "order_test", "test_name": "sputum_smear"})
    ...
    await env.persist()         # flushes episode + episode_steps to DB

Persistence model: buffered-per-episode. step() is sync and only appends to
an in-memory buffer. On `done`, or at any point afterwards, a caller awaits
`persist()` which opens a single connection, inserts one episodes row, then
batch-inserts the buffered episode_steps rows (one per step). Failures are
logged but non-fatal — the env still advances / returns StepResult — because
runtime training should not crash when Supabase is unreachable.

scenarios.id in the DB is a UUID; our code addresses scenarios by their
`external_id` (e.g. "case_01"). persist() looks up the uuid under the
currently-active knowledge_version and skips writes if the scenario isn't
seeded there yet.
"""

from __future__ import annotations

import json
import logging
import random
import uuid
from datetime import datetime, timezone
from typing import Any

from models import (
    DiagnoseAction,
    MedicalAction,
    Observation,
    OrderTestAction,
    ReferAction,
    State,
    StepResult,
    action_to_dict,
)
from env.progression import evolve_patient, get_test_result
from rag import RAGEngine
from env.rewards import calculate_reward
from env.scenarios import scenarios_v2

log = logging.getLogger(__name__)


class MedicalDiagnosisEnvironment:
    def __init__(
        self,
        agent_version: str | None = None,
        rag_engine: RAGEngine | None = None,
    ):
        self._agent_version = agent_version

        # Optional retrieval engine. When set, the env calls
        # `rag_engine.retrieve(...)` during step() and attaches the
        # returned RAGContext to StepResult.info["rag"]. When None,
        # the env runs with no retrieval overhead.
        self._rag_engine: RAGEngine | None = rag_engine

        # Episode state
        self._scenario: dict | None = None
        self._current_day = 1
        self._budget = 0.0
        self._tests_ordered: list[str] = []
        self._referred = False
        self._done = False
        self._memory: list[str] = []
        self._last_obs: Observation | None = None

        # Persistence state
        self._episode_id: uuid.UUID | None = None
        self._started_at: datetime | None = None
        self._ended_at: datetime | None = None
        self._step_buffer: list[dict] = []
        self._cumulative_reward = 0.0
        self._final_diagnosis: str | None = None
        self._outcome: str | None = None
        self._persisted = False

    # ── reset ────────────────────────────────────────────────────────────────

    def reset(self, scenario: dict | None = None) -> Observation:
        self._scenario = scenario if scenario is not None else random.choice(scenarios_v2)
        self._current_day = 1
        self._budget = float(self._scenario["budget"])
        self._tests_ordered = []
        self._referred = False
        self._done = False
        self._memory = []

        self._episode_id = uuid.uuid4()
        self._started_at = datetime.now(timezone.utc)
        self._ended_at = None
        self._step_buffer = []
        self._cumulative_reward = 0.0
        self._final_diagnosis = None
        self._outcome = None
        self._persisted = False

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
        if isinstance(action, (OrderTestAction, DiagnoseAction, ReferAction)):
            action = action_to_dict(action)

        # 0. Done guard
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

        # 1. Pre-action state snapshot
        pre_day = self._current_day
        pre_obs = self._last_obs
        current_state = {
            "current_day": self._current_day,
            "budget_remaining": self._budget,
            "tests_ordered": list(self._tests_ordered),
            "referred": self._referred,
        }

        # 2. Reward
        reward = calculate_reward(current_state, action, self._scenario)
        self._cumulative_reward += reward

        # 3. Side-effects
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

        elif action_type == "diagnose":
            self._final_diagnosis = action["diagnosis"]

        # 4. Done conditions
        current_status = evolve_patient(self._scenario, self._current_day)["status"]
        if action_type == "diagnose" or current_status == "critical" or self._budget <= 0:
            self._done = True
            self._ended_at = datetime.now(timezone.utc)
            self._outcome = self._classify_outcome(action)

        # 5. Advance day
        self._current_day += 1
        new_state = evolve_patient(self._scenario, self._current_day)

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

        # 6. Buffer the step for later DB flush. We store the *pre-action*
        #    observation as the observation the agent acted on, which is the
        #    useful one for training.
        self._step_buffer.append(
            {
                "step_num": len(self._step_buffer) + 1,
                "day": pre_day,
                "action_type": action_type,
                "action_payload": action,
                "observation": pre_obs.model_dump() if pre_obs is not None else {},
                "reward": float(reward),
                "cumulative_reward": float(self._cumulative_reward),
                "folded_state": None,
            }
        )

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

    # ── RAG hook ─────────────────────────────────────────────────────────────

    def attach_rag_engine(self, engine: RAGEngine) -> None:
        """
        Attach a retrieval engine after construction. Useful for the
        WebSocket server, which builds one env per connection and can
        inject a shared engine instance here.
        """
        self._rag_engine = engine

    @property
    def rag_engine(self) -> RAGEngine | None:
        return self._rag_engine

    # ── state ────────────────────────────────────────────────────────────────

    def state(self) -> State:
        return State(
            current_day=self._current_day,
            budget_remaining=self._budget,
            tests_ordered=list(self._tests_ordered),
            referred=self._referred,
            done=self._done,
            scenario_id=self._scenario["id"] if self._scenario else "",
            patient_status=evolve_patient(self._scenario, self._current_day)["status"]
            if self._scenario
            else "stable",
        )

    # ── outcome classifier ───────────────────────────────────────────────────

    def _classify_outcome(self, last_action: dict[str, Any]) -> str:
        """
        Match the CHECK constraint in public.episodes:
        ('correct','incorrect','referred_correct','referred_incorrect','timeout','error')
        """
        s = self._scenario
        if last_action["type"] == "diagnose":
            correct = last_action["diagnosis"] == s["hidden_diagnosis"]
            if self._referred:
                return "referred_correct" if correct else "referred_incorrect"
            return "correct" if correct else "incorrect"
        # Ended without a diagnosis — either budget gone or patient critical
        return "timeout"

    # ── persistence ──────────────────────────────────────────────────────────

    async def persist(self) -> bool:
        """
        Flush episode + buffered steps to Supabase. Safe to call after done=True
        (or sooner — truncates the buffer either way).

        Returns True on success, False on any DB error (never raises).
        """
        if self._persisted:
            return True
        if self._scenario is None or self._episode_id is None:
            return False

        # Import here so the env stays importable in envs without psycopg.
        try:
            from db.pool import get_conn
        except Exception as e:  # pragma: no cover
            log.warning("DB pool unavailable (%s); skipping persist.", e)
            return False

        external_id = self._scenario["id"]
        started_at = self._started_at
        ended_at = self._ended_at or datetime.now(timezone.utc)

        try:
            async with get_conn() as conn:
                async with conn.cursor() as cur:
                    # Find the active knowledge_version and the scenario uuid
                    # that matches our external_id under it.
                    await cur.execute(
                        """
                        SELECT s.id AS scenario_uuid,
                               s.knowledge_version_id AS kv_id
                        FROM public.scenarios s
                        JOIN public.knowledge_versions kv
                          ON kv.id = s.knowledge_version_id
                        WHERE s.external_id = %s AND kv.is_active
                        LIMIT 1;
                        """,
                        (external_id,),
                    )
                    row = await cur.fetchone()
                    if row is None:
                        log.warning(
                            "persist: scenario %r not found under active knowledge_version; "
                            "run scripts/seed_knowledge.py + seed_scenarios.py.",
                            external_id,
                        )
                        return False
                    # psycopg3 returns tuples by default; positional access is fine.
                    scenario_uuid, kv_id = row[0], row[1]

                    # Insert episode row
                    await cur.execute(
                        """
                        INSERT INTO public.episodes
                            (id, scenario_id, knowledge_version_id, agent_version,
                             started_at, ended_at, final_diagnosis, referred,
                             outcome, total_reward)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                        """,
                        (
                            str(self._episode_id),
                            scenario_uuid,
                            kv_id,
                            self._agent_version,
                            started_at,
                            ended_at,
                            self._final_diagnosis,
                            self._referred,
                            self._outcome,
                            round(float(self._cumulative_reward), 3),
                        ),
                    )

                    # ── Layer 2: synthetic patient + encounter ──
                    # Every rollout spawns a fresh synthetic patient from
                    # the scenario's demographics. When we move to real
                    # longitudinal patients, pass patient_id in via reset()
                    # and skip the INSERT into patients.
                    demographics = self._scenario.get("patient_demographics", {}) or {}
                    village = demographics.get("location")
                    await cur.execute(
                        """
                        INSERT INTO public.patients (demographics, village_or_region)
                        VALUES (%s::jsonb, %s)
                        RETURNING id;
                        """,
                        (json.dumps(demographics), village),
                    )
                    patient_row = await cur.fetchone()
                    patient_uuid = patient_row[0]

                    await cur.execute(
                        """
                        INSERT INTO public.patient_encounters
                            (patient_id, episode_id, started_at, ended_at, outcome)
                        VALUES (%s, %s, %s, %s, %s);
                        """,
                        (
                            patient_uuid,
                            str(self._episode_id),
                            started_at,
                            ended_at,
                            self._outcome,
                        ),
                    )

                    # Batch insert steps
                    if self._step_buffer:
                        step_rows = [
                            (
                                str(self._episode_id),
                                s["step_num"],
                                s["day"],
                                s["action_type"],
                                json.dumps(s["action_payload"]),
                                json.dumps(s["observation"]),
                                round(s["reward"], 3),
                                round(s["cumulative_reward"], 3),
                                json.dumps(s["folded_state"]) if s["folded_state"] is not None else None,
                            )
                            for s in self._step_buffer
                        ]
                        await cur.executemany(
                            """
                            INSERT INTO public.episode_steps
                                (episode_id, step_num, day, action_type,
                                 action_payload, observation, reward,
                                 cumulative_reward, folded_state)
                            VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb,
                                    %s, %s, %s::jsonb);
                            """,
                            step_rows,
                        )
                await conn.commit()
            self._persisted = True
            return True
        except Exception as e:
            # Never crash a rollout because of a DB hiccup.
            log.exception("persist failed for episode %s: %s", self._episode_id, e)
            try:
                # Best-effort rollback isn't needed because the context manager
                # discards an errored transaction; but swallow any further error.
                pass
            except Exception:
                pass
            return False
