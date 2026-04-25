"""
client.py — RuralDocEnv WebSocket client (EnvClient wrapper).

RuralDocEnv(EnvClient) connects to the FastAPI server defined in
server/app.py and exposes reset() / step() / state() over WebSocket,
matching the openenv EnvClient protocol.

Usage:
    import asyncio
    from env.client import RuralDocEnv

    async def main():
        env = RuralDocEnv(base_url="ws://localhost:8000")
        obs = await env.reset()
        result = await env.step({"type": "order_test", "test_name": "rapid_malaria_test"})
        result = await env.step({"type": "diagnose", "diagnosis": "malaria"})
        await env.close()

    asyncio.run(main())
"""
from __future__ import annotations

import json
import asyncio
import websockets
from models import Observation, StepResult, State


class RuralDocEnv:
    """
    WebSocket client for the RuralDoc environment server.

    Wraps the openenv EnvClient protocol: connects to the FastAPI /ws
    endpoint and serialises/deserialises Pydantic models.
    """

    def __init__(self, base_url: str = "ws://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self._ws = None

    # ── Connection lifecycle ──────────────────────────────────────────────────

    async def connect(self):
        """Open the WebSocket connection to the environment server."""
        uri = f"{self.base_url}/ws"
        self._ws = await websockets.connect(uri)

    async def close(self):
        """Close the WebSocket connection."""
        if self._ws:
            await self._ws.close()
            self._ws = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, *args):
        await self.close()

    # ── Environment API ───────────────────────────────────────────────────────

    async def reset(self, scenario_id: str | None = None) -> Observation:
        """
        Reset the environment and return the initial Observation.

        Args:
            scenario_id: optional scenario ID to pin (e.g. "case_01").
                         If None, the server picks randomly.
        """
        payload = {"command": "reset"}
        if scenario_id:
            payload["scenario_id"] = scenario_id
        await self._ws.send(json.dumps(payload))
        raw = await self._ws.recv()
        return Observation(**json.loads(raw))

    async def step(self, action: dict) -> StepResult:
        """
        Send one action and receive a StepResult.

        Args:
            action: plain dict — one of
                {"type": "order_test", "test_name": "<name>"}
                {"type": "diagnose",   "diagnosis": "<name>"}
                {"type": "refer"}
        """
        payload = {"command": "step", "action": action}
        await self._ws.send(json.dumps(payload))
        raw = await self._ws.recv()
        data = json.loads(raw)
        return StepResult(**data)

    async def state(self) -> State:
        """Return a snapshot of the current internal environment state."""
        payload = {"command": "state"}
        await self._ws.send(json.dumps(payload))
        raw = await self._ws.recv()
        return State(**json.loads(raw))
