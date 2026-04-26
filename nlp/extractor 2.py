"""
nlp/extractor.py — LLM-based structured extraction of patient complaints.

Takes free-text presenting complaint (English, Hindi, Hinglish, or mixed)
and returns a ParsedComplaint Pydantic model with structured symptom list,
urgency flags, and complaint duration.

APPROACH
--------
Single chat-completion call with JSON mode. The prompt is designed for
rural Indian PHC context: it handles transliterated Hindi symptom names
("bukhaar" → fever, "khansi" → cough), duration phrasing in colloquial
form ("teen din se" → 3 days), and severity markers ("bahut tez" → severe).

MODEL
-----
Uses MODEL_NAME env var (default gpt-4o-mini). Any OpenAI-compatible
endpoint works — HuggingFace, Ollama, etc.

USAGE
-----
    extractor = SymptomExtractor()
    result = await extractor.extract("Chronic cough, fever for 3 days, night sweats")
    # result.symptoms → [ExtractedSymptom(name="cough", ...), ...]
    # result.urgency_flags → []
    # result.raw_text → "Chronic cough, fever for 3 days, night sweats"
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Literal

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

log = logging.getLogger("ruraldoc.nlp.extractor")

# ── Pydantic output models ─────────────────────────────────────────────────────

class ExtractedSymptom(BaseModel):
    name: str                                      # normalised English name
    duration_days: int | None = None               # None if not mentioned
    severity: Literal["mild", "moderate", "severe", "unknown"] = "unknown"
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    original_phrase: str | None = None             # exact phrase from input


class ParsedComplaint(BaseModel):
    raw_text: str
    symptoms: list[ExtractedSymptom] = Field(default_factory=list)
    urgency_flags: list[str] = Field(default_factory=list)
    # e.g. ["chest_pain", "unconscious", "difficulty_breathing", "seizure",
    #        "snake_bite", "high_fever_>104F", "unable_to_walk"]
    complaint_duration_days: int | None = None     # overall complaint duration if stated
    model_used: str = ""
    parse_ms: int = 0


# ── Extraction prompt ──────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a clinical NLP assistant for rural Indian Primary Health Centers (PHCs).
Your job is to extract structured medical information from patient presenting complaints.
The text may be in English, Hindi (transliterated), or a mix (Hinglish).

Common Hindi/Hinglish symptom terms:
- bukhaar / tez bukhaar → fever (tez = high/intense)
- khansi / khaansi → cough
- sardard / sar dard → headache
- pet dard / pait dard → abdominal pain
- ulti / vomiting → vomiting
- dast / loose motions → diarrhea
- thakaan / kamzori → fatigue/weakness
- sans lene mein takleef → difficulty breathing
- seena dard / seena mein dard → chest pain
- aankhon mein dard / aankh dard → eye pain
- raat ko paseena → night sweats
- kaan dard → ear pain
- naak se paani → runny nose
- teen din se / 3 din se → for 3 days

Duration phrasing:
- "teen din se" / "3 days" → duration_days: 3
- "ek hafte se" / "week" → duration_days: 7
- "mahine bhar se" / "month" → duration_days: 30
- "chronic" without specifics → duration_days: null

Urgency flags to extract (use these exact strings when present):
chest_pain, difficulty_breathing, unconscious, seizure, snake_bite,
high_fever, severe_bleeding, unable_to_walk, altered_consciousness,
severe_abdominal_pain, trauma

Return ONLY valid JSON matching this schema:
{
  "symptoms": [
    {
      "name": "<normalised English symptom name, lowercase>",
      "duration_days": <int or null>,
      "severity": "<mild|moderate|severe|unknown>",
      "confidence": <0.0–1.0>,
      "original_phrase": "<exact phrase from input>"
    }
  ],
  "urgency_flags": ["<flag>", ...],
  "complaint_duration_days": <int or null>
}

Rules:
- Always use normalised English for "name" even if input was Hindi
- Extract every distinct symptom mentioned
- If severity is not stated, use "unknown"
- confidence reflects how certain you are this is a symptom (vs. context)
- urgency_flags is independent of symptoms — flag anything life-threatening"""


# ── Extractor class ────────────────────────────────────────────────────────────

class SymptomExtractor:
    """
    LLM-backed extractor. One instance is safe to share across requests
    (AsyncOpenAI client is thread/async-safe).
    """

    def __init__(self, model: str | None = None) -> None:
        self.model = model or os.environ.get("MODEL_NAME", "gpt-4o-mini")
        self._client = AsyncOpenAI(
            api_key=os.environ.get("HF_TOKEN") or os.environ.get("OPENAI_API_KEY", ""),
            base_url=os.environ.get("API_BASE_URL", "https://api.openai.com/v1"),
        )

    async def extract(self, text: str) -> ParsedComplaint:
        """
        Extract structured complaint from free text.

        Args:
            text    Raw presenting complaint string from the patient form.

        Returns:
            ParsedComplaint with symptoms, urgency_flags, durations.
            Never raises — on LLM error returns a ParsedComplaint with
            empty symptoms and logs a warning.
        """
        if not text or not text.strip():
            return ParsedComplaint(raw_text=text, model_used=self.model)

        t0 = time.monotonic()
        try:
            resp = await self._client.chat.completions.create(
                model=self.model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text.strip()},
                ],
                temperature=0,        # deterministic — we want consistent extraction
                max_tokens=1024,
            )

            raw_json = resp.choices[0].message.content or "{}"
            parsed = json.loads(raw_json)

            symptoms = [
                ExtractedSymptom(**s)
                for s in parsed.get("symptoms", [])
            ]
            urgency_flags = parsed.get("urgency_flags", [])
            complaint_duration_days = parsed.get("complaint_duration_days")

        except Exception as exc:
            log.warning("SymptomExtractor.extract failed for %r: %s", text[:60], exc)
            symptoms = []
            urgency_flags = []
            complaint_duration_days = None

        parse_ms = int((time.monotonic() - t0) * 1000)

        return ParsedComplaint(
            raw_text=text,
            symptoms=symptoms,
            urgency_flags=urgency_flags,
            complaint_duration_days=complaint_duration_days,
            model_used=self.model,
            parse_ms=parse_ms,
        )


# Module-level singleton
extractor = SymptomExtractor()
