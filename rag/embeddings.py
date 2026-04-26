"""
rag/embeddings.py — Multi-mode Embedder: text → float vector.

Three transport modes, selected by env vars:

  1. LOCAL (recommended for dev)
        Set LOCAL_EMBED=1.
        Uses `sentence-transformers` directly — no API calls, works offline.
        Install: pip install sentence-transformers
        Dim is auto-detected from the model.

  2. HF feature-extraction (serverless, free)
        Default when LOCAL_EMBED is unset.
        POSTs to https://router.huggingface.co/hf-inference/models/{model}
        Requires HF_TOKEN with "Inference Providers" permission enabled
        in your HF account settings (Settings → Inference Providers).
        NOTE: The old api-inference.huggingface.co/models/ path is 404 as of 2025.

  3. OpenAI-compatible /v1/embeddings (TEI dedicated endpoint, paid)
        Set EMBED_API_BASE_URL=https://<your-endpoint>.hf.space/v1
        Embedder auto-detects the /v1 suffix and uses this path.

Embedder env vars:
    LOCAL_EMBED         — set to "1" to use sentence-transformers locally (no API)
    EMBED_API_BASE_URL  — base URL (modes 2 & 3). Default: https://router.huggingface.co/hf-inference
    EMBED_API_KEY       — bearer token. Falls back to HF_TOKEN.
    EMBED_MODEL         — HF model id.
                          Default: sentence-transformers/all-MiniLM-L6-v2 (384-dim, fast, ~90 MB)
                          Production: BAAI/bge-large-en-v1.5 (1024-dim, ~1.3 GB, apply migration 002)

LLM env vars (env/inference.py — DO NOT confuse with the above):
    API_BASE_URL        — e.g. https://api-inference.huggingface.co/v1
    HF_TOKEN            — HF bearer token (also fallback for EMBED_API_KEY)
    MODEL_NAME          — e.g. meta-llama/Llama-3.1-8B-Instruct

Schema compatibility:
    all-MiniLM-L6-v2  → 384-dim  → apply db/migrations/003_embed_dims_384.sql
    bge-large-en-v1.5 → 1024-dim → apply db/migrations/002_embed_dims_1024.sql

Used by:
    nlp/vocab.py               — embed symptom names at startup
    nlp/matcher.py             — embed extracted complaint text for pgvector match
    scripts/seed_embeddings.py — populate the *_embeddings tables

Embedding tables in schema:
    disease_embeddings, symptom_embeddings, patient_embeddings, case_embeddings
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

import httpx


log = logging.getLogger("ruraldoc.rag.embeddings")

# Default embedding model — override via EMBED_MODEL env var.
# all-MiniLM-L6-v2: 384 dims, fast, ~90 MB. Good for local dev.
# BAAI/bge-large-en-v1.5: 1024 dims, ~1.3 GB. Use for production + apply migration 002.
DEFAULT_EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_DIM = 384  # matches all-MiniLM-L6-v2; update if you change the model

# Default base URL: new HF inference router (requires Inference Providers token permission).
# Old path api-inference.huggingface.co/models/ was removed in 2025.
DEFAULT_BASE_URL = "https://router.huggingface.co/hf-inference"

# Known model → dim lookup (avoids needing to load the model just to get dims).
_MODEL_DIMS: dict[str, int] = {
    "sentence-transformers/all-MiniLM-L6-v2": 384,
    "sentence-transformers/all-MiniLM-L12-v2": 384,
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2": 384,
    "BAAI/bge-large-en-v1.5": 1024,
    "BAAI/bge-base-en-v1.5": 768,
    "BAAI/bge-small-en-v1.5": 384,
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
}


def _resolve_config() -> tuple[str, str, str]:
    """Resolve (base_url, api_key, model). Fail loud if in HTTP mode and no token."""
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
    return base_url, api_key, model


def _dim_for_model(model: str, fallback: int = DEFAULT_DIM) -> int:
    """Return the known output dimension for a model id."""
    # Strip org prefix for lookup (e.g. "sentence-transformers/all-MiniLM-L6-v2" → check full key first)
    return _MODEL_DIMS.get(model, fallback)


class Embedder:
    """
    Async embedder — three modes: local (sentence-transformers), HF HTTP, or OpenAI TEI.

    Usage:
        embedder = Embedder()
        vec = await embedder.embed("fever for three days")
        # vec is list[float], length depends on model

    Set LOCAL_EMBED=1 in your environment for offline/local use:
        Local mode uses sentence-transformers directly, no network calls.

    The class is safe to instantiate at module import time — everything is
    built lazily on first call.
    """

    def __init__(self, model: str | None = None, dim: int | None = None) -> None:
        self._model_override = model
        self._dim_override = dim
        self._client: httpx.AsyncClient | None = None
        self._mode: str | None = None  # "local" | "feature_extraction" | "openai"
        self._url: str | None = None
        self._api_key: str | None = None
        self._model: str | None = None
        self._st_model: Any = None  # sentence_transformers.SentenceTransformer instance
        self._dim: int = dim or DEFAULT_DIM

    @property
    def dim(self) -> int:
        return self._dim

    # ── Lazy init ────────────────────────────────────────────────────────────

    def _ensure_config(self) -> None:
        if self._mode is not None:
            return

        base_url, api_key, model = _resolve_config()
        self._api_key = api_key
        self._model = self._model_override or model

        # Resolve dim: explicit override → known lookup → default
        if self._dim_override is not None:
            self._dim = self._dim_override
        else:
            self._dim = _dim_for_model(self._model, DEFAULT_DIM)

        if os.environ.get("LOCAL_EMBED", "").strip() == "1":
            self._mode = "local"
            log.info(
                "Embedder: LOCAL_EMBED=1 → using sentence-transformers locally "
                "(model=%s, dim=%d)", self._model, self._dim
            )
            return

        # HTTP modes — require an API key
        if not api_key:
            raise RuntimeError(
                "Embedder: no API key. Set EMBED_API_KEY (or HF_TOKEN), "
                "or set LOCAL_EMBED=1 to use sentence-transformers locally."
            )

        # Auto-select HTTP transport by base URL suffix
        if base_url.rstrip("/").endswith("/v1"):
            self._mode = "openai"
            self._url = f"{base_url}/embeddings"
        else:
            self._mode = "feature_extraction"
            # New HF router path: /models/{model} under the hf-inference base
            self._url = f"{base_url}/models/{self._model}"

        log.info(
            "Embedder: mode=%s url=%s model=%s dim=%d",
            self._mode, self._url, self._model, self._dim,
        )

    def _get_http_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(60.0, connect=10.0),
                headers={"Authorization": f"Bearer {self._api_key}"},
            )
        return self._client

    def _get_st_model(self) -> Any:
        """Lazily load SentenceTransformer. Raises ImportError with a helpful message."""
        if self._st_model is None:
            try:
                from sentence_transformers import SentenceTransformer  # type: ignore
            except ImportError:
                raise ImportError(
                    "sentence-transformers is not installed. "
                    "Run: pip install sentence-transformers\n"
                    "Or install the rag extras: pip install -e '.[rag]'"
                )
            log.info("Loading SentenceTransformer model: %s", self._model)
            self._st_model = SentenceTransformer(self._model)
            # Update dim from the loaded model (authoritative)
            inferred_dim = self._st_model.get_sentence_embedding_dimension()
            if inferred_dim and inferred_dim != self._dim:
                log.info(
                    "Embedder dim updated from model: %d → %d",
                    self._dim, inferred_dim,
                )
                self._dim = inferred_dim
        return self._st_model

    # ── Public API ───────────────────────────────────────────────────────────

    async def embed(self, text: str) -> list[float]:
        """Embed a single string. Returns list[float] of length self.dim."""
        vecs = await self.embed_batch([text])
        return vecs[0]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Embed multiple strings. Returns list of vectors in input order.

        In local mode: runs in a thread executor so it doesn't block the event loop.
        In HTTP mode: max ~32 inputs per call is safe for HF serverless.
        """
        self._ensure_config()
        clean = [t.strip().replace("\n", " ") for t in texts]

        if self._mode == "local":
            return await self._embed_local(clean)
        if self._mode == "openai":
            return await self._embed_openai(clean)
        return await self._embed_feature_extraction(clean)

    # ── Transport: local sentence-transformers ────────────────────────────────

    async def _embed_local(self, texts: list[str]) -> list[list[float]]:
        """
        Encode via sentence-transformers in a thread executor.
        SentenceTransformer.encode() is CPU/GPU-bound and not async-native.
        """
        loop = asyncio.get_event_loop()
        st = self._get_st_model()

        def _encode() -> list[list[float]]:
            vecs = st.encode(texts, convert_to_numpy=True, show_progress_bar=False)
            return [v.tolist() for v in vecs]

        result = await loop.run_in_executor(None, _encode)
        return result

    # ── Transport: HF feature-extraction (new router) ─────────────────────────

    async def _embed_feature_extraction(
        self, texts: list[str], retries: int = 3, backoff: float = 2.0,
    ) -> list[list[float]]:
        """
        POST {base}/models/{model}  (HF inference router)

        Response shapes:
          • Sentence-transformers: [[f, ...], ...]   (N, dim)
          • Raw transformer:       [[[f, ...]]]      (N, T, dim) — mean-pooled

        If you get 403 "insufficient permissions", enable Inference Providers
        in your HF account: https://huggingface.co/settings/inference-providers
        Or switch to LOCAL_EMBED=1.
        """
        payload = {
            "inputs": texts,
            "options": {"wait_for_model": True, "use_cache": True},
        }
        client = self._get_http_client()
        last_exc: Exception | None = None

        for attempt in range(retries):
            try:
                resp = await client.post(self._url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                return _normalize_embeddings(data, expected_dim=self.dim)
            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                if status == 403:
                    raise RuntimeError(
                        f"HF Inference Router 403: token lacks 'Inference Providers' permission. "
                        f"Either enable it at https://huggingface.co/settings/inference-providers "
                        f"or set LOCAL_EMBED=1 to use sentence-transformers locally."
                    ) from e
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
                    log.warning("HF embed transport error (%s); retry in %.1fs", e, wait)
                    await asyncio.sleep(wait)
                    last_exc = e
                    continue
                raise

        if last_exc is not None:
            raise last_exc
        raise RuntimeError("embed_batch retry loop exited without result")

    # ── Transport: OpenAI-compatible (TEI) ───────────────────────────────────

    async def _embed_openai(self, texts: list[str]) -> list[list[float]]:
        """POST {base}/embeddings — OpenAI-compatible (TEI dedicated endpoints)."""
        payload = {"input": texts, "model": self._model}
        client = self._get_http_client()
        resp = await client.post(self._url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        items = sorted(data.get("data", []), key=lambda x: x.get("index", 0))
        vecs = [item["embedding"] for item in items]
        if vecs and len(vecs[0]) != self.dim:
            log.warning(
                "Embedder dim mismatch: expected %d, got %d. "
                "Update EMBED_MODEL and apply the matching migration.",
                self.dim, len(vecs[0]),
            )
        return vecs

    # ── Cleanup ──────────────────────────────────────────────────────────────

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None


# ─────────────────────────────────────────────────────────────────────────────
#  Response normalization (HTTP modes only)
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_embeddings(data: Any, expected_dim: int) -> list[list[float]]:
    """
    Coerce the HF feature-extraction response into [[float, ...], ...].

    Handles three shapes:
      1. Flat list of floats — single input, sentence-transformer pooled
      2. List of pooled vectors — (N, dim)
      3. List of token sequences — (N, T, dim) — mean-pooled here
    """
    if not isinstance(data, list):
        raise RuntimeError(f"Unexpected embed response (not a list): {type(data)}")

    # Shape 1: flat list of floats
    if data and isinstance(data[0], (int, float)):
        if len(data) != expected_dim:
            log.warning("Embed dim mismatch: got %d, expected %d", len(data), expected_dim)
        return [list(map(float, data))]

    # Shape 2: list of pooled vectors — (N, dim)
    if data and isinstance(data[0], list) and data[0] and isinstance(data[0][0], (int, float)):
        result = [list(map(float, v)) for v in data]
        if result and len(result[0]) != expected_dim:
            log.warning("Embed dim mismatch: got %d, expected %d", len(result[0]), expected_dim)
        return result

    # Shape 3: per-token sequences — (N, T, dim). Mean-pool over T.
    if data and isinstance(data[0], list) and data[0] and isinstance(data[0][0], list):
        pooled: list[list[float]] = []
        for seq in data:
            if not seq:
                pooled.append([0.0] * expected_dim)
                continue
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
        print(f"Mode: LOCAL_EMBED={os.environ.get('LOCAL_EMBED', 'unset')}")
        vec = await e.embed("fever night sweats weight loss Delhi 34M")
        ok = "OK" if len(vec) == e.dim else f"DIM MISMATCH (got {len(vec)}, expected {e.dim})"
        print(
            f"[{ok}] embed() → {len(vec)}-dim vector "
            f"(model={e._model}, mode={e._mode})"
        )
        vecs = await e.embed_batch(["chest pain", "headache fever"])
        print(f"[OK] embed_batch(2) → {len(vecs)} vectors × dim={len(vecs[0]) if vecs else '?'}")
        await e.aclose()

    asyncio.run(_smoke())
