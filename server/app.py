"""
server/app.py — FastAPI WebSocket server for RuralDocEnv.

Creates a FastAPI app using the openenv create_fastapi_app() factory,
wrapping MedicalDiagnosisEnvironment.

Run locally:
    uvicorn server.app:app --host 0.0.0.0 --port 8000

Docker:
    docker build -t ruraldoc-env ./server
    docker run -p 8000:8000 ruraldoc-env
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from server.environment import MedicalDiagnosisEnvironment

app = FastAPI(
    title="RuralDocEnv",
    description="Rural Indian PHC clinical reasoning simulator — openenv-compatible",
    version="0.1.0",
)

# One environment instance per connection
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    env = MedicalDiagnosisEnvironment()

    try:
        while True:
            raw = await websocket.receive_text()
            payload = json.loads(raw)
            command = payload.get("command")

            if command == "reset":
                scenario_id = payload.get("scenario_id")
                from rural_doc_env.scenarios import scenarios_v2
                scenario = None
                if scenario_id:
                    scenario = next((s for s in scenarios_v2 if s["id"] == scenario_id), None)
                obs = env.reset(scenario=scenario)
                await websocket.send_text(obs.model_dump_json())

            elif command == "step":
                action = payload.get("action", {})
                result = env.step(action)
                await websocket.send_text(result.model_dump_json())

            elif command == "state":
                state = env.state()
                await websocket.send_text(state.model_dump_json())

            else:
                await websocket.send_text(json.dumps({"error": f"Unknown command: {command}"}))

    except WebSocketDisconnect:
        pass


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
            "status", "budget_remaining", "day", "memory"
        ],
    }
