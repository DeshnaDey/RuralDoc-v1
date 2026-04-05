"""
client.py — HTTP and WebSocket clients for MedicalDiagnosisEnv.

EnvClient        — abstract base with a common interface
RuralDocEnv      — synchronous HTTP client (httpx)
AsyncRuralDocEnv — async HTTP client (httpx.AsyncClient)
_WSSession       — async WebSocket session (websockets)

Environment variables:
    ENV_URL  — base URL of the server  (default: http://localhost:8000)

Usage (sync HTTP):
    env = RuralDocEnv()
    obs = env.reset(scenario_id="case_07")
    result = env.step({"type": "order_test", "test_name": "rapid_malaria_test"})
    result = env.step({"type": "diagnose", "diagnosis": "malaria"})

Usage (async WebSocket):
    async with _WSSession("ws://localhost:8000/ws") as ws:
        obs  = await ws.reset(scenario_id="case_07")
        r    = await ws.step({"type": "refer"})
        r    = await ws.step({"type": "diagnose", "diagnosis": "tuberculosis"})
"""

from __future__ import annotations

import asyncio
import json
import os
from abc import ABC, abstractmethod
from typing import Any

import httpx
import websockets


# ── Base class ────────────────────────────────────────────────────────────────

class EnvClient(ABC):
    """Abstract interface shared by all RuralDoc client implementations."""

    @abstractmethod
    def reset(self, scenario_id: str | None = None) -> dict:
        """Start a new episode. Returns the initial Observation as a dict."""

    @abstractmethod
    def step(self, action: dict) -> dict:
        """Take one action. Returns a StepResult dict."""

    @abstractmethod
    def state(self) -> dict:
        """Return the current State dict."""

    @abstractmethod
    def scenarios(self) -> list[dict]:
        """Return the list of available scenarios."""

    @abstractmethod
    def health(self) -> dict:
        """Liveness check. Returns {"status": "ok"} on success."""


# ── Synchronous HTTP client ───────────────────────────────────────────────────

class RuralDocEnv(EnvClient):
    """
    Synchronous HTTP client wrapping the FastAPI server.

    Args:
        base_url: HTTP base URL of the server.  Defaults to $ENV_URL or
                  http://localhost:8000.
        timeout:  Request timeout in seconds (default 30).
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._base = (base_url or os.getenv("ENV_URL", "http://localhost:8000")).rstrip("/")
        self._client = httpx.Client(base_url=self._base, timeout=timeout)

    # ── Context manager support ───────────────────────────────────────────────

    def __enter__(self) -> "RuralDocEnv":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    # ── EnvClient interface ───────────────────────────────────────────────────

    def reset(self, scenario_id: str | None = None) -> dict:
        """POST /reset — returns the initial Observation dict."""
        body = {}
        if scenario_id is not None:
            body["scenario_id"] = scenario_id
        resp = self._client.post("/reset", json=body)
        resp.raise_for_status()
        return resp.json()

    def step(self, action: dict) -> dict:
        """POST /step — returns a StepResult dict."""
        resp = self._client.post("/step", json={"action": action})
        resp.raise_for_status()
        return resp.json()

    def state(self) -> dict:
        """GET /state — returns the current State dict."""
        resp = self._client.get("/state")
        resp.raise_for_status()
        return resp.json()

    def scenarios(self) -> list[dict]:
        """GET /scenarios — returns list of scenario summaries."""
        resp = self._client.get("/scenarios")
        resp.raise_for_status()
        return resp.json()["scenarios"]

    def health(self) -> dict:
        """GET /health — returns {"status": "ok"}."""
        resp = self._client.get("/health")
        resp.raise_for_status()
        return resp.json()


# ── Async HTTP client ─────────────────────────────────────────────────────────

class AsyncRuralDocEnv(EnvClient):
    """
    Asynchronous HTTP client wrapping the FastAPI server.

    Must be used with `await` and as an async context manager:

        async with AsyncRuralDocEnv() as env:
            obs = await env.reset()
            result = await env.step({"type": "refer"})
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._base = (base_url or os.getenv("ENV_URL", "http://localhost:8000")).rstrip("/")
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "AsyncRuralDocEnv":
        self._client = httpx.AsyncClient(base_url=self._base, timeout=self._timeout)
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    def _check(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("Use AsyncRuralDocEnv as an async context manager.")
        return self._client

    # ── EnvClient interface (async versions) ──────────────────────────────────

    async def reset(self, scenario_id: str | None = None) -> dict:  # type: ignore[override]
        body = {}
        if scenario_id is not None:
            body["scenario_id"] = scenario_id
        resp = await self._check().post("/reset", json=body)
        resp.raise_for_status()
        return resp.json()

    async def step(self, action: dict) -> dict:  # type: ignore[override]
        resp = await self._check().post("/step", json={"action": action})
        resp.raise_for_status()
        return resp.json()

    async def state(self) -> dict:  # type: ignore[override]
        resp = await self._check().get("/state")
        resp.raise_for_status()
        return resp.json()

    async def scenarios(self) -> list[dict]:  # type: ignore[override]
        resp = await self._check().get("/scenarios")
        resp.raise_for_status()
        return resp.json()["scenarios"]

    async def health(self) -> dict:  # type: ignore[override]
        resp = await self._check().get("/health")
        resp.raise_for_status()
        return resp.json()


# ── WebSocket session ─────────────────────────────────────────────────────────

class _WSSession:
    """
    Async WebSocket session over /ws.

    Usage:
        async with _WSSession("ws://localhost:8000/ws") as ws:
            obs = await ws.reset(scenario_id="case_01")
            result = await ws.step({"type": "refer"})
            state = await ws.state()
    """

    def __init__(self, ws_url: str | None = None) -> None:
        base = os.getenv("ENV_URL", "http://localhost:8000").rstrip("/")
        # Convert http(s):// → ws(s)://
        base_ws = base.replace("http://", "ws://").replace("https://", "wss://")
        self._url = ws_url or f"{base_ws}/ws"
        self._conn = None

    async def __aenter__(self) -> "_WSSession":
        self._conn = await websockets.connect(self._url)
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def _send(self, msg: dict) -> dict:
        if self._conn is None:
            raise RuntimeError("Use _WSSession as an async context manager.")
        await self._conn.send(json.dumps(msg))
        raw = await self._conn.recv()
        data = json.loads(raw)
        if "error" in data:
            raise RuntimeError(f"Server error: {data['error']}")
        return data

    async def reset(self, scenario_id: str | None = None) -> dict:
        msg: dict = {"cmd": "reset"}
        if scenario_id is not None:
            msg["scenario_id"] = scenario_id
        return await self._send(msg)

    async def step(self, action: dict) -> dict:
        return await self._send({"cmd": "step", "action": action})

    async def state(self) -> dict:
        return await self._send({"cmd": "state"})


# ── Smoke test (requires a running server) ────────────────────────────────────
if __name__ == "__main__":
    import sys

    base = os.getenv("ENV_URL", "http://localhost:8000")
    print(f"Testing against {base} …\n")

    try:
        with RuralDocEnv(base_url=base) as env:
            print("health:", env.health())
            scenarios = env.scenarios()
            print(f"scenarios available: {len(scenarios)}")

            # Full malaria episode
            malaria_id = next(s["id"] for s in scenarios if "alaria" in s.get("disease", ""))
            obs = env.reset(scenario_id=malaria_id)
            print(f"\nreset → day={obs['day']} budget={obs['budget_remaining']} status={obs['status']}")

            r1 = env.step({"type": "order_test", "test_name": "rapid_malaria_test"})
            print(f"step1 → reward={r1['reward']:.4f} done={r1['done']}")

            r2 = env.step({"type": "diagnose", "diagnosis": "malaria"})
            print(f"step2 → reward={r2['reward']:.4f} done={r2['done']}")

            s = env.state()
            print(f"state → done={s['done']} budget={s['budget_remaining']}")

    except httpx.ConnectError:
        print(
            "Could not connect to server. Start it first:\n"
            "  cd server && uvicorn app:app --port 8000",
            file=sys.stderr,
        )
        sys.exit(1)
