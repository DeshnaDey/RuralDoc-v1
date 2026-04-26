"""
nlp/prompt_builder.py — Groq-backed pre-processor + prompt assembler.

Stage 1 of the unstructured-input pipeline:

    raw_text  ─►  PromptBuilder.build()  ─►  BuiltPrompt
                  │
                  ├── (Groq) language detection + Hinglish→English gloss
                  ├── (Groq) speciality / category hint
                  └── deterministic prompt template assembly with
                      schema, few-shots, and the cleaned input

The cleaned text is what gets handed to the heavy LLM (Ollama) in stage 2.
Keeping pre-processing on Groq is deliberate:
  • Groq inference is sub-second, so the user-facing latency is dominated
    by Ollama, not by this prep step.
  • Hinglish detection / cleanup off the local model frees Ollama's context
    for the structured extraction, which is the harder part.

GRACEFUL DEGRADATION
--------------------
If GROQ_API_KEY is not set, build() short-circuits: it returns a BuiltPrompt
that wraps the raw text plus the default template — no enrichment, no
translation. The downstream Ollama call still works; you just lose the
nice cleaning step. This is intentional so dev environments don't depend
on a Groq key.

ENV VARS
--------
    GROQ_API_KEY        — bearer token (optional)
    GROQ_BASE_URL       — default https://api.groq.com/openai/v1
    GROQ_MODEL          — default llama-3.1-8b-instant (cheap + fast)
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any

import httpx

log = logging.getLogger("ruraldoc.nlp.prompt_builder")

DEFAULT_GROQ_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_GROQ_MODEL = "llama-3.1-8b-instant"


# ── Output type ───────────────────────────────────────────────────────────────


@dataclass
class BuiltPrompt:
    """
    What the prompt builder hands to the Ollama stage.

    cleaned_text : free-text complaint after Groq normalisation.
                   Falls back to raw_text if Groq is disabled or failed.
    raw_text     : exact original input — preserved so we can audit /
                   round-trip it into the symptom_extraction_log row.
    language     : detected language code (en, hi, hinglish, mixed)
    hint_category: rough body system hint from Groq (e.g. "respiratory")
                   used to prime Ollama's reasoning. None if disabled.
    messages     : list[{"role","content"}] ready for the Ollama call —
                   includes system, optional context, and user turns.
    meta         : free-form dict with timing + model info for the log.
    """
    cleaned_text: str
    raw_text: str
    language: str = "unknown"
    hint_category: str | None = None
    messages: list[dict[str, str]] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)


# ── Templates ─────────────────────────────────────────────────────────────────

# This is the same schema the Ollama model is expected to return.
# Keep it in lock-step with nlp/extractor.py:ParsedComplaint / ExtractedSymptom.
EXTRACTION_SYSTEM_PROMPT = """You are a clinical NLP service for rural Indian Primary Health Centers (PHCs).

Extract structured medical information from a patient's presenting complaint.
The text may be English, Hindi, transliterated Hinglish, or any mix.

Common Hinglish symptom terms:
  bukhaar/tez bukhaar = fever       khansi = cough           sardard = headache
  pet dard = abdominal pain         ulti = vomiting          dast = diarrhea
  thakaan/kamzori = fatigue         seena dard = chest pain
  sans lene mein takleef = dyspnoea raat ko paseena = night sweats
  aankh dard = eye pain             kaan dard = ear pain     pilia = jaundice
  saanp ne kaata = snake bite       behosh = unconscious     fit/miraagi = seizure

Duration phrasing:
  "teen din se" / "3 din se" / "for 3 days"  →  3
  "ek hafte se" / "for a week"               →  7
  "mahine bhar se" / "for a month"           →  30
  "chronic" with no number                   →  null

Urgency flags (use these exact strings):
  chest_pain, difficulty_breathing, unconscious, seizure, snake_bite,
  high_fever, severe_bleeding, unable_to_walk, altered_consciousness,
  severe_abdominal_pain, trauma

Return ONLY valid JSON matching this exact schema — no prose, no fences:
{
  "symptoms": [
    {
      "name": "<lowercase canonical English>",
      "duration_days": <int or null>,
      "severity": "mild|moderate|severe|unknown",
      "confidence": <0.0-1.0>,
      "original_phrase": "<exact slice of input>"
    }
  ],
  "urgency_flags": ["<flag>", ...],
  "complaint_duration_days": <int or null>
}

Rules:
- normalise "name" to English even if input is Hindi
- include every distinct symptom mentioned (no duplicates)
- severity = "unknown" when not stated
- confidence reflects how certain this token is a symptom
- urgency_flags is independent of symptoms — flag any life-threat
"""


# Pre-processor prompt for Groq. Returns JSON with cleaned text + language + hint.
PREPROCESS_SYSTEM_PROMPT = """You are a fast pre-processor for clinical NLP.

Given a free-text patient complaint (English, Hindi, Hinglish, or mixed),
return a single JSON object — no prose, no fences:

{
  "cleaned": "<English-normalised version, but keep medical terms verbatim>",
  "language": "en | hi | hinglish | mixed | other",
  "hint_category": "respiratory | gastrointestinal | neurological | cardiovascular | musculoskeletal | infectious | dermatological | ophthalmological | ent | metabolic | trauma | obstetric | general"
}

Rules:
- Do NOT extract symptoms — that's a downstream job.
- "cleaned" should preserve the patient's intent; translate Hinglish
  symptom phrases to common English, but keep numbers/durations.
- "hint_category" is a single best-guess body system based on the
  complaint as a whole.
"""


# ── Builder ───────────────────────────────────────────────────────────────────


class PromptBuilder:
    """
    Stage-1 pre-processor. Optional Groq call, deterministic fallback.

    Usage:
        pb = PromptBuilder()
        built = await pb.build("Tez bukhaar teen din se, sardard")
        # → built.cleaned_text, built.messages ready for Ollama
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self._api_key = api_key or os.environ.get("GROQ_API_KEY", "")
        self._base_url = (base_url or os.environ.get("GROQ_BASE_URL")
                          or DEFAULT_GROQ_BASE_URL).rstrip("/")
        self._model = model or os.environ.get("GROQ_MODEL", DEFAULT_GROQ_MODEL)
        self._client: httpx.AsyncClient | None = None

    @property
    def enabled(self) -> bool:
        """True iff Groq pre-processing is wired up."""
        return bool(self._api_key)

    def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(15.0, connect=5.0),
                headers={"Authorization": f"Bearer {self._api_key}"},
            )
        return self._client

    # ── Public API ───────────────────────────────────────────────────────

    async def build(self, raw_text: str, *, patient_meta: dict | None = None) -> BuiltPrompt:
        """
        Run pre-processing + assemble the chat-completion messages.

        patient_meta is an optional dict with demographics-like fields
        (age, gender, location). When provided it's injected as system
        context so Ollama can use endemic-disease priors.
        """
        text = (raw_text or "").strip()
        if not text:
            return BuiltPrompt(
                cleaned_text="",
                raw_text=raw_text,
                messages=[
                    {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                    {"role": "user", "content": ""},
                ],
                meta={"groq_used": False, "reason": "empty_input"},
            )

        cleaned = text
        language = "unknown"
        hint = None
        groq_meta: dict[str, Any] = {"groq_used": False}

        if self.enabled:
            try:
                cleaned, language, hint = await self._preprocess_with_groq(text)
                groq_meta = {
                    "groq_used": True,
                    "groq_model": self._model,
                    "language": language,
                    "hint_category": hint,
                }
            except Exception as exc:  # never fatal
                log.warning("Groq preprocess failed (%s) — falling back to raw", exc)
                groq_meta = {"groq_used": False, "groq_error": str(exc)[:200]}

        messages = self._compose_messages(
            cleaned_text=cleaned,
            raw_text=text,
            hint=hint,
            patient_meta=patient_meta,
        )

        return BuiltPrompt(
            cleaned_text=cleaned,
            raw_text=raw_text,
            language=language,
            hint_category=hint,
            messages=messages,
            meta=groq_meta,
        )

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    # ── Internals ────────────────────────────────────────────────────────

    async def _preprocess_with_groq(self, text: str) -> tuple[str, str, str | None]:
        """
        Hit Groq's chat-completions endpoint with PREPROCESS_SYSTEM_PROMPT,
        force JSON mode, return (cleaned, language, hint_category).
        """
        payload = {
            "model": self._model,
            "temperature": 0,
            "max_tokens": 256,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": PREPROCESS_SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
        }
        resp = await self._http().post(
            f"{self._base_url}/chat/completions",
            json=payload,
        )
        resp.raise_for_status()
        body = resp.json()
        raw = body["choices"][0]["message"]["content"] or "{}"
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            log.warning("Groq returned non-JSON pre-process payload: %s", raw[:120])
            return text, "unknown", None

        cleaned = (obj.get("cleaned") or text).strip()
        language = (obj.get("language") or "unknown").strip().lower()
        hint = obj.get("hint_category")
        if isinstance(hint, str):
            hint = hint.strip().lower() or None
        else:
            hint = None
        return cleaned, language, hint

    def _compose_messages(
        self,
        *,
        cleaned_text: str,
        raw_text: str,
        hint: str | None,
        patient_meta: dict | None,
    ) -> list[dict[str, str]]:
        """Assemble the chat array for the Ollama extraction call."""
        messages: list[dict[str, str]] = [
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
        ]

        # Optional context block — only adds noise when there's nothing to add.
        ctx_lines: list[str] = []
        if hint:
            ctx_lines.append(f"likely body system: {hint}")
        if patient_meta:
            for k in ("age", "gender", "location"):
                v = patient_meta.get(k)
                if v:
                    ctx_lines.append(f"{k}: {v}")
        if ctx_lines:
            messages.append({
                "role": "system",
                "content": "Context (advisory, do not invent symptoms from this):\n"
                           + "\n".join(f"  - {l}" for l in ctx_lines),
            })

        # User turn carries both the cleaned and the raw form so the model
        # can resolve ambiguous Hinglish phrases by checking the original.
        if cleaned_text == raw_text:
            user_block = cleaned_text
        else:
            user_block = (
                f"Cleaned: {cleaned_text}\n"
                f"Original: {raw_text}"
            )
        messages.append({"role": "user", "content": user_block})
        return messages


# Module-level singleton so the httpx client is reused across requests.
prompt_builder = PromptBuilder()
