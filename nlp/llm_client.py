"""
nlp/llm_client.py — Ollama-backed structured extraction client.

Stage 2 of the unstructured-input pipeline:

    BuiltPrompt  ─►  OllamaClient.extract_json()  ─►  dict

Ollama exposes an OpenAI-compatible endpoint at
    http://<host>:11434/v1/chat/completions
so we use the same shape as the rest of the codebase. JSON-mode is supported
via Ollama's "format": "json" hint AND OpenAI's response_format. We send
both — Ollama ignores what it doesn't understand.

WHY OLLAMA HERE
---------------
The user-facing extraction step is the heavy one (long system prompt,
strict schema, plenty of vocab). Running it locally means:
  • zero per-request cost
  • no rate-limit concerns when batching past complaints
  • fully offline once the model is pulled

Drop-in alternatives — anything that speaks /v1/chat/completions, e.g.
vllm or a hosted OpenAI-compatible endpoint — work by changing
OLLAMA_BASE_URL.

ENV VARS
--------
    OLLAMA_BASE_URL   default http://localhost:11434/v1
    OLLAMA_MODEL      default llama3.1:8b-instruct-q4_K_M
                      (any chat model you've `ollama pull`-ed will work)
    OLLAMA_API_KEY    optional bearer token (most local setups don't need it)
    OLLAMA_TIMEOUT_S  default 90 (CPU-only inference can be slow first call)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

log = logging.getLogger("ruraldoc.nlp.llm_client")

DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434/v1"
DEFAULT_OLLAMA_MODEL = "llama3.1:8b-instruct-q4_K_M"
DEFAULT_TIMEOUT_S = 90.0


# ── Output type ───────────────────────────────────────────────────────────────


@dataclass
class LLMResponse:
    """
    Result of a chat-completion call.

    json_obj   : parsed JSON dict (None if model returned non-JSON / errored)
    raw_text   : exact string content returned by the model — kept so the
                 validator can show it in error logs and re-prompts can see
                 what actually came back.
    model      : model id that responded (e.g. llama3.1:8b-instruct-q4_K_M)
    parse_ms   : wall-clock latency including network
    error      : populated only on transport / HTTP failure
    """
    json_obj: dict[str, Any] | None
    raw_text: str = ""
    model: str = ""
    parse_ms: int = 0
    error: str | None = None


# ── Client ────────────────────────────────────────────────────────────────────


class OllamaClient:
    """
    Thin async wrapper around Ollama's OpenAI-compatible chat endpoint.

    One instance is safe to share across concurrent requests — the underlying
    httpx.AsyncClient supports parallel calls. Lazy-init defers the client
    until first use so module import doesn't open sockets.
    """

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout_s: float | None = None,
        api_key: str | None = None,
    ) -> None:
        self._base_url = (
            base_url
            or os.environ.get("OLLAMA_BASE_URL")
            or DEFAULT_OLLAMA_BASE_URL
        ).rstrip("/")
        self._model = model or os.environ.get("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
        self._timeout = float(
            timeout_s
            if timeout_s is not None
            else os.environ.get("OLLAMA_TIMEOUT_S", DEFAULT_TIMEOUT_S)
        )
        self._api_key = api_key or os.environ.get("OLLAMA_API_KEY", "")
        self._client: httpx.AsyncClient | None = None

    @property
    def model(self) -> str:
        return self._model

    @property
    def base_url(self) -> str:
        return self._base_url

    def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            headers: dict[str, str] = {}
            if self._api_key:
                headers["Authorization"] = f"Bearer {self._api_key}"
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout, connect=10.0),
                headers=headers,
            )
        return self._client

    # ── Public API ───────────────────────────────────────────────────────

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        json_mode: bool = True,
    ) -> LLMResponse:
        """
        POST /chat/completions, return raw model text + parsed JSON if applicable.

        Sends BOTH `response_format: {"type":"json_object"}` (OpenAI-style) and
        a top-level "format": "json" so it works whether you point at Ollama,
        vllm, or any other OAI-compatible server.
        """
        payload: dict[str, Any] = {
            "model": self._model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
            payload["format"] = "json"  # Ollama-native hint

        url = f"{self._base_url}/chat/completions"
        t0 = time.monotonic()
        try:
            resp = await self._http().post(url, json=payload)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            body = ""
            try:
                body = e.response.text[:300]
            except Exception:
                pass
            log.warning("Ollama HTTP %s: %s", e.response.status_code, body)
            return LLMResponse(
                json_obj=None,
                raw_text="",
                model=self._model,
                parse_ms=int((time.monotonic() - t0) * 1000),
                error=f"HTTP {e.response.status_code}: {body}",
            )
        except (httpx.TransportError, httpx.TimeoutException) as e:
            log.warning("Ollama transport error: %s", e)
            return LLMResponse(
                json_obj=None,
                raw_text="",
                model=self._model,
                parse_ms=int((time.monotonic() - t0) * 1000),
                error=f"Transport error: {e}",
            )

        elapsed_ms = int((time.monotonic() - t0) * 1000)
        try:
            body = resp.json()
            content = body["choices"][0]["message"]["content"] or ""
        except Exception as exc:
            log.warning("Ollama non-OpenAI response shape: %s", exc)
            return LLMResponse(
                json_obj=None,
                raw_text="",
                model=self._model,
                parse_ms=elapsed_ms,
                error=f"Bad response shape: {exc}",
            )

        json_obj: dict[str, Any] | None = None
        if json_mode:
            json_obj = _extract_json_object(content)

        return LLMResponse(
            json_obj=json_obj,
            raw_text=content,
            model=self._model,
            parse_ms=elapsed_ms,
        )

    async def health(self) -> bool:
        """Ping the /models endpoint — useful for startup checks."""
        try:
            resp = await self._http().get(f"{self._base_url}/models")
            return resp.status_code == 200
        except Exception:
            return False

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None


# ── Helpers ───────────────────────────────────────────────────────────────────


def _extract_json_object(text: str) -> dict[str, Any] | None:
    """
    Be lenient about JSON parsing — Ollama models occasionally wrap output
    in ``` fences or stray prose despite json_mode being requested.
    """
    text = (text or "").strip()
    if not text:
        return None

    # Direct parse — fast path
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        pass

    # Strip common ``` fences
    if text.startswith("```"):
        # remove first fence line
        first_nl = text.find("\n")
        if first_nl != -1:
            text = text[first_nl + 1 :]
        # remove trailing fence
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
        try:
            obj = json.loads(text.strip())
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            pass

    # Last resort: find the outermost {...} block
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        candidate = text[start : end + 1]
        try:
            obj = json.loads(candidate)
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            return None
    return None


# Module-level singleton — reuse across requests.
ollama_client = OllamaClient()


# ── Smoke test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    async def _smoke() -> None:
        client = OllamaClient()
        ok = await client.health()
        print(f"health: {'OK' if ok else 'UNREACHABLE'} ({client.base_url})")
        if not ok:
            return
        resp = await client.chat(
            [
                {"role": "system", "content": "Reply with JSON: {\"pong\": true}"},
                {"role": "user", "content": "ping"},
            ]
        )
        print(f"model: {resp.model}  ms: {resp.parse_ms}")
        print(f"json:  {resp.json_obj}")
        print(f"raw:   {resp.raw_text[:120]}")
        await client.aclose()

    asyncio.run(_smoke())
