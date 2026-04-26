"""
rag/embeddings.py — HF-backed Embedder: text → 1024-dim vector.

The embedder POSTs to HuggingFace's serverless feature-extraction endpoint.
This is the free, no-OpenAI path. The LLM client (env/inference.py) is
SEPARATE from this embedder on purpose; see env-vars below.

Model: BAAI/bge-large-en-v1.5 (1024 dims).
    Top-of-MTEB English retrieval, warm on HF serverless, free with HF_TOKEN.

Why HTTP (not the openai client)?
    HF's serverless API (api-inference.huggingface.co) does NOT expose
    /v1/embeddings — only /pipeline/feature-extraction/{model}. We POST raw
    JSON. To use a TEI Inference Endpoint instead (paid, OpenAI-compatible),
    point EMBED_API_BASE_URL at it and the embedder will switch to the
    /v1/embeddings code path automatically.

Embedder env vars (this file only):
    EMBED_API_BASE_URL  — base URL.
                          Default: https://api-inference.huggingface.co
                          Set to https://<endpoint>.hf.space/v1 for TEI.
    EMBED_API_KEY       — bearer token. Falls back to HF_TOKEN.
    EMBED_MODEL         — HF model id. Default: BAAI/bge-large-en-v1.5

LLM env vars (env/inference.py — DO NOT confuse with the above):
    API_BASE_URL        — e.g. https://api-inference.huggingface.co/v1
    HF_TOKEN            — HF bearer token (also fallback for EMBED_API_KEY)
    MODEL_NAME          — e.g. meta-llama/Llama-3.1-8B-Instruct

Used by:
    nlp/vocab.py       — embed symptom names at startup
    nlp/matcher.py     — embed extracted complaint text for pgvector match
    scripts/seed_embeddings.py — populate the *_embeddings tables

Embedding tables in schema (all vector(1024) after migration 002):
    disease_embeddings, symptom_embeddings, patient_embeddings, case_embeddings
"""

from __future__ import annotations

import asyncio
import logging
import os

import httpx


log = logging.getLogger("ruraldoc.rag.embeddings")

# Default embedding model — override via EMBED_MODEL env var.
# bge-large-en-v1.5: 1024 dims, matches the vector(1024) columns post-migration.
DEFAULT_EMBED_MODEL = "BAAI/bge-large-en-v1.5"
DEFAULT_DIM = 1024

# Default base URL: HF serverless inference. To switch to a TEI dedicated
# Inference Endpoint, set EMBED_API_BASE_URL=https://<your-endpoint>.hf.space/v1.
DEFAULT_BASE_URL = "https://api-inference.huggingface.co"


def _resolve_config() -> tuple[str, str, str]:
    """Resolve (base_url, api_key, model). Fail loud if no token."""
    api_key = (
        os.environ.get("EMBED_API_KEY")
        or os.environ.get("HF_TOKEN")
        or ""
    )
    base_url = (
        os.environ.get("EMBED_API_BASE_URL")
        or DEFAULT_BASE_URL
    ).rstrip("/")
    model = os.environ.get("EMBED_MODEL", DEFAULT_EMBED_MODEL)

    if not api_key:
        raise RuntimeError(
            "Embedder has no API key. Set EMBED_API_KEY (or HF_TOKEN) in .env. "
            "RAG will not work otherwise."
        )
    return base_url, api_key, model


class Embedder:
    """
    Async embedder backed by HF feature-extraction (or any TEI / OpenAI-
    compatible /v1/embeddings endpoint).

    Usage:
        embedder = Embedder()
        vec = await embedder.embed("fever for three days")
        # vec is a list[float] of length 1024 for bge-large-en-v1.5

    Two transport modes, auto-selected by base URL:
      • HF feature-extraction:
          POST {base}/pipeline/feature-extraction/{model}
          body: {"inputs": [...], "options": {"wait_for_model": true}}
      • OpenAI-compatible /v1/embeddings (TEI):
          POST {base}/embeddings   (when base ends in /v1)
          body: {"input": [...], "model": "..."}

    The class is safe to instantiate at module import time — the HTTP client
    is built lazily on first call.
    """

    dim: int = DEFAULT_DIM

    def __init__(self, model: str | None = None, dim: int | None = None) -> None:
        # model can be overridden per-instance, but defaults to env var
        self._model_override = model
        if dim is not None:
            self.dim = dim
        self._client: httpx.AsyncClient | None = None
        self._mode: str | None = None  # "feature_extraction" | "openai"
        self._url: str | None = None
        self._api_key: str | None = None
        self._model: str | None = None

    # ── Lazy init ────────────────────────────────────────────────────────────

    def _ensure_config(self) -> None:
        if self._url is not None:
            return
        base_url, api_key, model = _resolve_config()
        self._api_key = api_key
        self._model = self._model_override or model

        # Detect transport: if the base ends in /v1 we assume TEI / OpenAI shape.
        if base_url.rstrip("/").endswith("/v1"):
            self._mode = "openai"
            self._url = f"{base_url}/embeddings"
        else:
            self._mode = "feature_extraction"
            self._url = f"{base_url}/models/{self._model}"

        log.info(
            "Embedder configured: mode=%s url=%s model=%s",
            self._mode, self._url, self._model,
        )

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(60.0, connect=10.0),
                headers={"Authorization": f"Bearer {self._api_key}"},
            )
        return self._client

    # ── Public API ───────────────────────────────────────────────────────────

    async def embed(self, text: str) -> list[float]:
        """Embed a single string. Returns a list[float] of length self.dim."""
        vecs = await self.embed_batch([text])
        return vecs[0]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Embed multiple strings in one API call.
        Returns a list of vectors in the same order as the input.

        On HF serverless, max ~64 inputs per request is a safe ceiling
        (the API limits payload size, not strictly count). Caller should
        chunk above ~32 for reliability.
        """
        self._ensure_config()
        clean = [t.strip().replace("\n", " ") for t in texts]

        if self._mode == "openai":
            return await self._embed_openai(clean)
        return await self._embed_feature_extraction(clean)

    # ── Transport: HF feature-extraction ─────────────────────────────────────

    async def _embed_feature_extraction(
        self, texts: list[str], retries: int = 3, backoff: float = 2.0,
    ) -> list[list[float]]:
        """
        POST {base}/pipeline/feature-extraction/{model}

        Response shapes (depends on model):
          • Sentence-transformers (bge-*):  [[f, ...], [f, ...]]   (N, dim)
          • Raw transformer:                [[[f, ...]]]           (N, T, dim)

        We assume sentence-transformer shape (the default for bge-large-en-v1.5)
        and validate the dim. If a model returns per-token vectors we mean-pool.
        """
        payload = {
            "inputs": texts,
            "options": {"wait_for_model": True, "use_cache": True},
        }
        client = self._get_client()
        last_exc: Exception | None = None

        for attempt in range(retries):
            try:
                resp = await client.post(self._url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                return _normalize_embeddings(data, expected_dim=self.dim)
            except httpx.HTTPStatusError as e:
                # 503 with estimated_time means model is still warming up.
                # 429 means rate limited.
                status = e.response.status_code
                if status in (503, 429) and attempt < retries - 1:
                    wait = backoff * (2 ** attempt)
                    log.warning(
                        "HF embed got %d (attempt %d/%d); retry in %.1fs",
                        status, attempt + 1, retries, wait,
                    )
                    await asyncio.sleep(wait)
                    last_exc = e
                    continue
                raise
            except (httpx.TransportError, httpx.TimeoutException) as e:
                if attempt < retries - 1:
                    wait = backoff * (2 ** attempt)
                    log.warning(
                        "HF embed transport error (%s); retry in %.1fs",
                        e, wait,
                    )
                    await asyncio.sleep(wait)
                    last_exc = e
                    continue
                raise

        if last_exc is not None:
            raise last_exc
        raise RuntimeError("embed_batch retry loop exited without result")

    # ── Transport: OpenAI-compatible (TEI) ───────────────────────────────────

    async def _embed_openai(self, texts: list[str]) -> list[list[float]]:
        """
        POST {base}/embeddings  (OpenAI-compatible — used by TEI Inference
        Endpoints).
        """
        payload = {"input": texts, "model": self._model}
        client = self._get_client()
        resp = await client.post(self._url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        items = sorted(data.get("data", []), key=lambda x: x.get("index", 0))
        vecs = [item["embedding"] for item in items]
        if vecs and len(vecs[0]) != self.dim:
            log.warning(
                "Embedder dim mismatch: expected %d, got %d. "
                "Update Embedder.dim and the schema.",
                self.dim, len(vecs[0]),
            )
        return vecs

    # ── Cleanup ──────────────────────────────────────────────────────────────

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None


# ─────────────────────────────────────────────────────────────────────────────
#  Response normalization
# ─────────────────────────────────────────────────────────────────────────────


def _normalize_embeddings(data, expected_dim: int) -> list[list[float]]:
    """
    Coerce the HF feature-extraction response into [[float, ...], ...].

    Handles three shapes:
      1. Single input as string → flat [float, ...]
      2. List of inputs, sentence-transformer pooled → [[float, ...], ...]
      3. List of inputs, raw transformer per-token → [[[float, ...]]] (mean-pool)
    """
    if not isinstance(data, list):
        raise RuntimeError(f"Unexpected embed response (not a list): {type(data)}")

    # Shape 1: flat list of floats — single input was sent
    if data and isinstance(data[0], (int, float)):
        if len(data) != expected_dim:
            log.warning("Embed dim mismatch: got %d, expected %d", len(data), expected_dim)
        return [list(map(float, data))]

    # Shape 2: list of pooled vectors — N x dim
    if data and isinstance(data[0], list) and data[0] and isinstance(data[0][0], (int, float)):
        # Already (N, dim)
        result = [list(map(float, v)) for v in data]
        if result and len(result[0]) != expected_dim:
            log.warning(
                "Embed dim mismatch: got %d, expected %d",
                len(result[0]), expected_dim,
            )
        return result

    # Shape 3: list of token sequences — N x T x dim. Mean-pool over T.
    if data and isinstance(data[0], list) and data[0] and isinstance(data[0][0], list):
        pooled: list[list[float]] = []
        for seq in data:
            if not seq:
                pooled.append([0.0] * expected_dim)
                continue
            # Mean across tokens
            T = len(seq)
            D = len(seq[0])
            mean_vec = [0.0] * D
            for tok in seq:
                for i, v in enumerate(tok):
                    mean_vec[i] += v / T
            pooled.append(mean_vec)
        return pooled

    raise RuntimeError(f"Unrecognised embed response shape: {data!r:.200}")


# Module-level singleton — import and reuse across the app:
#   from rag.embeddings import embedder
#   vec = await embedder.embed("chest pain")
embedder = Embedder()


# ─────────────────────────────────────────────────────────────────────────────
#  Smoke test — `python -m rag.embeddings`
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    async def _smoke() -> None:
        e = Embedder()
        vec = await e.embed("fever night sweats weight loss Delhi 34M")
        ok = "OK" if len(vec) == e.dim else "DIM MISMATCH"
        print(
            f"[{ok}] embed('fever ...') returned {len(vec)}-dim vector "
            f"(expected={e.dim}, model={e._model}, mode={e._mode})"
        )
        # batch sanity
        vecs = await e.embed_batch(["chest pain", "headache fever"])
        print(f"[OK] embed_batch(2 inputs) returned {len(vecs)} vectors of "
              f"dim={len(vecs[0]) if vecs else '?'}")
        await e.aclose()

    asyncio.run(_smoke())
