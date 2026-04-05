"""
server/app.py — FastAPI application for MedicalDiagnosisEnv.

REST endpoints:
    POST /reset                 — start new episode
    POST /step                  — take one action
    GET  /state                 — current internal state
    GET  /health                — liveness probe
    GET  /scenarios             — list available scenario IDs

WebSocket:
    /ws                         — stream reset/step/state over a single connection

Message format over WebSocket:
    Client sends:  {"cmd": "reset"} | {"cmd": "step", "action": <action dict>} | {"cmd": "state"}
    Server replies: the same JSON shapes as the REST endpoints
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel, ValidationError

from environment import MedicalDiagnosisEnvironment
from scenarios.scenario2 import scenarios_v2
from models import MedicalActionAdapter


# ── Request schemas ───────────────────────────────────────────────────────────

class ResetRequest(BaseModel):
    scenario_id: str | None = None  # None → random


class StepRequest(BaseModel):
    action: dict  # {"type": "order_test", ...} etc.


# ── Factory ───────────────────────────────────────────────────────────────────

def create_fastapi_app(env: MedicalDiagnosisEnvironment | None = None) -> FastAPI:
    """
    Build and return the FastAPI application.

    Args:
        env: An already-constructed MedicalDiagnosisEnvironment, or None to
             create a fresh one.  Useful for testing — pass in a pre-seeded env.
    """
    if env is None:
        env = MedicalDiagnosisEnvironment()

    app = FastAPI(
        title="RuralDoc — MedicalDiagnosisEnv API",
        description=(
            "OpenEnv-compatible REST + WebSocket interface for the "
            "rural PHC diagnostic simulator."
        ),
        version="0.1.0",
    )

    # ── Scenario index (built once at startup) ────────────────────────────────
    _scenario_by_id: dict[str, dict] = {s["id"]: s for s in scenarios_v2}

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _obs_json(obs) -> dict:
        return obs.model_dump()

    def _state_json(state) -> dict:
        return state.model_dump()

    def _step_json(result) -> dict:
        return result.model_dump()

    # ── REST endpoints ────────────────────────────────────────────────────────

    @app.get("/health")
    def health():
        """Liveness probe."""
        return {"status": "ok"}

    @app.get("/scenarios")
    def list_scenarios():
        """Return a list of available scenario IDs and their display names."""
        return {
            "scenarios": [
                {
                    "id": s["id"],
                    "disease": s.get("disease_name", s["id"]),
                    "requires_referral": s.get("requires_referral", False),
                    "budget": s["budget"],
                    "critical_window_days": s["critical_window_days"],
                }
                for s in scenarios_v2
            ]
        }

    @app.post("/reset")
    def reset(req: ResetRequest = ResetRequest()):
        """
        Start a new episode.

        Body (optional):
            {"scenario_id": "case_01"}   — pick a specific scenario
            {}                            — pick at random
        """
        scenario = None
        if req.scenario_id is not None:
            scenario = _scenario_by_id.get(req.scenario_id)
            if scenario is None:
                raise HTTPException(
                    status_code=404,
                    detail=(
                        f"Unknown scenario_id '{req.scenario_id}'. "
                        f"Valid IDs: {list(_scenario_by_id.keys())}"
                    ),
                )
        obs = env.reset(scenario=scenario)
        return _obs_json(obs)

    @app.post("/step")
    def step(req: StepRequest):
        """
        Take one action.

        Body:
            {"action": {"type": "order_test", "test_name": "sputum_smear"}}
            {"action": {"type": "diagnose",   "diagnosis": "tuberculosis"}}
            {"action": {"type": "refer"}}
        """
        try:
            MedicalActionAdapter.validate_python(req.action)
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.errors())

        result = env.step(req.action)
        return _step_json(result)

    @app.get("/state")
    def state():
        """Return the current internal environment state."""
        return _state_json(env.state())

    # ── WebSocket endpoint ────────────────────────────────────────────────────

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """
        Single-connection WebSocket interface.

        Client sends JSON commands; server replies with JSON.

        Commands:
            {"cmd": "reset"}
            {"cmd": "reset", "scenario_id": "case_01"}
            {"cmd": "step",  "action": {"type": "refer"}}
            {"cmd": "state"}

        Replies mirror the REST endpoint responses.
        """
        await websocket.accept()
        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    await websocket.send_json({"error": "Invalid JSON"})
                    continue

                cmd = msg.get("cmd")

                if cmd == "reset":
                    scenario_id = msg.get("scenario_id")
                    scenario = None
                    if scenario_id is not None:
                        scenario = _scenario_by_id.get(scenario_id)
                        if scenario is None:
                            await websocket.send_json(
                                {"error": f"Unknown scenario_id '{scenario_id}'"}
                            )
                            continue
                    obs = env.reset(scenario=scenario)
                    await websocket.send_json(_obs_json(obs))

                elif cmd == "step":
                    action = msg.get("action")
                    if action is None:
                        await websocket.send_json(
                            {"error": "'action' field required for step"}
                        )
                        continue
                    try:
                        MedicalActionAdapter.validate_python(action)
                    except ValidationError as exc:
                        await websocket.send_json({"error": exc.errors()})
                        continue
                    result = env.step(action)
                    await websocket.send_json(_step_json(result))

                elif cmd == "state":
                    await websocket.send_json(_state_json(env.state()))

                else:
                    await websocket.send_json(
                        {
                            "error": (
                                f"Unknown command '{cmd}'. "
                                "Use: reset | step | state"
                            )
                        }
                    )

        except WebSocketDisconnect:
            pass

    return app


# ── Default application instance ──────────────────────────────────────────────
# Used by Uvicorn: `uvicorn app:app`

app = create_fastapi_app()


# ── Dev entrypoint ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
