"""
server/app.py — FastAPI WebSocket server for RuralDocEnv.

Wraps the canonical MedicalDiagnosisEnvironment behind a WebSocket so the
frontend can drive rollouts from the UI. Every time an episode finishes
(`result.done == True`) or the socket disconnects mid-episode, the server
awaits `env.persist()`, which writes the episode + its steps to Supabase
AND (via persist's Layer-2 path) a patient + patient_encounter row. That
is the mechanism by which Layers 2-4 get updated on every run.

Run locally:
    uvicorn server.app:app --host 0.0.0.0 --port 8000

Docker:
    docker build -t ruraldoc-env -f server/Dockerfile .
    docker run -p 8000:8000 --env-file .env ruraldoc-env
"""

from __future__ import annotations

import sys
if sys.platform == "win32":
    import asyncio as _asyncio
    _asyncio.set_event_loop_policy(_asyncio.WindowsSelectorEventLoopPolicy())

import asyncio
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from db.pool import close_pool, get_pool
from env.environment import MedicalDiagnosisEnvironment
from env.scenarios import scenarios_v2
from nlp.vocab import SymptomVocab
from rag.embeddings import Embedder
from backend.routes.extract import router as extract_router

log = logging.getLogger("ruraldoc.server")

# Limit concurrent WebSocket environments to avoid resource exhaustion
MAX_CONCURRENT_ENVS = 64
_semaphore = asyncio.Semaphore(MAX_CONCURRENT_ENVS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warm the pool at startup so the first WS connection isn't slow.
    pool = await get_pool()
    app.state.pool = pool
    app.state.embedder = Embedder()
    app.state.vocab = SymptomVocab()
    await app.state.vocab.load(pool, version_id=1)
    app.state.version_id = 1
    log.info("DB pool opened.")
    try:
        yield
    finally:
        await close_pool()
        log.info("DB pool closed.")


app = FastAPI(
    title="RuralDocEnv",
    description="Rural Indian PHC clinical reasoning simulator — openenv-compatible",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(extract_router)


@app.get("/")
async def root():
    return {
        "name": "RuralDocEnv",
        "status": "running",
        "description": "Rural Indian PHC clinical reasoning simulator",
        "endpoints": {
            "health": "/health",
            "info": "/info",
            "websocket": "/ws",
        },
        "huggingface": "https://huggingface.co/spaces/Kiddy007/RuralDocEnv",
    }


@app.post("/reset")
async def http_reset(body: dict = {}):
    """Stateless HTTP reset — spins up a fresh env, resets it, and returns the obs."""
    env = MedicalDiagnosisEnvironment()
    scenario = None
    scenario_id = body.get("scenario_id") if body else None
    if scenario_id:
        scenario = next((s for s in scenarios_v2 if s["id"] == scenario_id), None)
    obs = env.reset(scenario=scenario)
    return obs.model_dump()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Protocol: each client message is JSON with a `command`. Supported:
      {"command": "reset",    "scenario_id": "case_01" | null, "agent_version": "..."}
      {"command": "step",     "action": {...}}
      {"command": "state"}
      {"command": "persist"}           # optional manual flush

    Concurrency: at most MAX_CONCURRENT_ENVS connections are active at once;
    additional connections block on the semaphore until a slot frees up.
    """
    async with _semaphore:
        await websocket.accept()
        env: MedicalDiagnosisEnvironment | None = None
        episode_finished_persisted = False

        try:
            while True:
                raw = await websocket.receive_text()
                payload = json.loads(raw)
                command = payload.get("command")

                if command == "reset":
                    # If the previous episode is still unflushed, persist it so
                    # we never silently drop rollout data.
                    if env is not None and not episode_finished_persisted:
                        await env.persist()

                    agent_version = payload.get("agent_version")
                    env = MedicalDiagnosisEnvironment(agent_version=agent_version)
                    episode_finished_persisted = False

                    scenario_id = payload.get("scenario_id")
                    scenario = None
                    if scenario_id:
                        scenario = next(
                            (s for s in scenarios_v2 if s["id"] == scenario_id), None
                        )
                    obs = env.reset(scenario=scenario)
                    await websocket.send_text(obs.model_dump_json())

                elif command == "step":
                    if env is None:
                        await websocket.send_text(
                            json.dumps({"error": "must call reset before step"})
                        )
                        continue

                    action = payload.get("action", {})
                    result = env.step(action)
                    await websocket.send_text(result.model_dump_json())

                    # On episode completion, flush to DB once.
                    if result.done and not episode_finished_persisted:
                        ok = await env.persist()
                        episode_finished_persisted = True
                        if not ok:
                            log.warning(
                                "persist() returned False — episode data not written to Supabase."
                            )

                elif command == "state":
                    if env is None:
                        await websocket.send_text(json.dumps({"error": "no active episode"}))
                        continue
                    await websocket.send_text(env.state().model_dump_json())

                elif command == "persist":
                    if env is None:
                        await websocket.send_text(json.dumps({"error": "no active episode"}))
                        continue
                    ok = await env.persist()
                    episode_finished_persisted = episode_finished_persisted or ok
                    await websocket.send_text(json.dumps({"persisted": ok}))

                else:
                    await websocket.send_text(
                        json.dumps({"error": f"Unknown command: {command}"})
                    )

        except WebSocketDisconnect:
            # If the frontend vanished mid-episode, still persist whatever
            # steps were buffered. This is the safety net that guarantees
            # every real rollout lands in Supabase.
            if env is not None and not episode_finished_persisted:
                try:
                    await env.persist()
                except Exception as e:  # pragma: no cover
                    log.exception("post-disconnect persist failed: %s", e)


@app.get("/health")
async def health():
    return {"status": "ok", "env": "RuralDocEnv"}


@app.get("/info")
async def info():
    return {
        "name": "RuralDocEnv",
        "description": "Rural Indian PHC clinical reasoning simulator",
        "action_space": ["order_test", "diagnose", "refer"],
        "observation_fields": [
            "patient", "symptoms", "vitals", "available_tests",
            "status", "budget_remaining", "day", "memory",
        ],
    }


def main():
    """CLI entrypoint — used by `server` script in pyproject.toml.
    Port 7860 matches the HuggingFace Spaces default.
    """
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()
