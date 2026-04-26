"""
nlp/extractor.py — LLM-based structured extraction of patient complaints.

Takes free-text presenting complaint (English, Hindi, Hinglish, or mixed)
and returns a ParsedComplaint Pydantic model with structured symptom list,
urgency flags, and complaint duration.

APPROACH
--------
Two-layer extraction:
  1. LLM (primary): single chat-completion call with JSON output. Handles
     nuanced Hindi/Hinglish/English mixed text, duration phrasing, severity.
     Requires a working OpenAI-compatible endpoint (API_BASE_URL + MODEL_NAME).
  2. Regex fallback (secondary): fires when LLM is unavailable or returns
     empty symptoms (e.g. HF serverless endpoint not working). Keyword
     dictionary covers the most common PHC presentations in English + Hinglish.
     Lower confidence than LLM; marks each result with confidence=0.6.

MODEL
-----
Uses MODEL_NAME env var. Any OpenAI-compatible endpoint works — HuggingFace,
Ollama, local vllm, etc. HF serverless /v1/chat/completions is currently
unreliable for free-tier models; fix is deferred until local trained model
is available (see handoff notes).

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
import re
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


# ── Regex fallback ────────────────────────────────────────────────────────────
#
# Keyword → normalised English name map. Keys are lowercase regex patterns;
# values are the canonical symptom names used throughout the system.
# Covers common rural Indian PHC presentations in English + Hinglish.
#
_SYMPTOM_PATTERNS: list[tuple[str, str]] = [
    # Fever
    (r"\b(fever|bukhaar|tez bukhaar|pyrexia|febrile)\b", "fever"),
    # Cough
    (r"\b(cough|khansi|khaansi|khaasi|dry cough|productive cough)\b", "cough"),
    # Headache
    (r"\b(headache|head\s*ache|sardard|sar\s*dard|migraine)\b", "headache"),
    # Abdominal pain
    (r"\b(abdominal\s*pain|stomach\s*pain|belly\s*pain|pet\s*dard|pait\s*dard|abdominal\s*ache)\b", "abdominal pain"),
    # Vomiting
    (r"\b(vomit(?:ing)?|nausea|ulti|uulti|nauseous)\b", "vomiting"),
    # Diarrhoea
    (r"\b(diarrh?oea|diarrhea|loose\s*motions?|dast|watery\s*stool)\b", "diarrhea"),
    # Fatigue / weakness
    (r"\b(fatigue|weakness|tired(?:ness)?|thakaan|kamzori|lethargy|malaise)\b", "fatigue"),
    # Dyspnoea
    (r"\b(breath(?:less(?:ness)?)?|dyspn[oe]?a|difficulty\s*breath(?:ing)?|sans\s*lene\s*mein\s*takleef|shortness\s*of\s*breath)\b", "difficulty breathing"),
    # Chest pain
    (r"\b(chest\s*pain|seena\s*dard|seena\s*mein\s*dard|chest\s*tightness)\b", "chest pain"),
    # Night sweats
    (r"\b(night\s*sweat|raat\s*ko\s*paseena|nocturnal\s*diaphoresis)\b", "night sweats"),
    # Muscle/joint pain
    (r"\b(muscle\s*ache|myalgia|joint\s*pain|arthralgia|body\s*ache|badan\s*dard)\b", "body ache"),
    # Rash
    (r"\b(rash|skin\s*rash|eruption|spots?\s*on\s*skin)\b", "rash"),
    # Jaundice
    (r"\b(jaundice|yellow(?:ing)?\s*(?:of\s*)?(?:eyes?|skin)?|pilia)\b", "jaundice"),
    # Rigors / chills
    (r"\b(rigor|chill|shiver(?:ing)?)\b", "chills"),
    # Runny nose
    (r"\b(runny\s*nose|rhinorrh?oea|naak\s*se\s*paani|nasal\s*discharge)\b", "runny nose"),
    # Ear pain
    (r"\b(ear\s*(?:pain|ache)|kaan\s*dard|otalgia)\b", "ear pain"),
    # Eye symptoms
    (r"\b(eye\s*pain|aankh\s*dard|red\s*eye|conjunctivitis|aankhon\s*mein\s*dard)\b", "eye pain"),
    # Swelling
    (r"\b(swelling|oedema|edema|soojan)\b", "swelling"),
    # Decreased urine output
    (r"\b(decreased\s*urine|oliguria|no\s*urine|peshab\s*kam)\b", "decreased urine output"),
    # Snake bite
    (r"\b(snake\s*bite|snakebite|saanp\s*ne\s*kaata)\b", "snake bite"),
    # Convulsion / seizure
    (r"\b(convulsion|seizure|fit|epilepsy|miraagi)\b", "seizure"),
    # Unconscious
    (r"\b(unconscious(?:ness)?|unresponsive|faint(?:ing)?|behosh)\b", "unconsciousness"),
    # Bleeding
    (r"\b(bleeding|haemorrhage|hemorrhage|blood\s*in\s*(?:stool|urine|vomit))\b", "bleeding"),
    # Pallor / anaemia
    (r"\b(pale|pallor|anaemia|anemia)\b", "pallor"),
    # Sore throat
    (r"\b(sore\s*throat|throat\s*pain|gale\s*mein\s*dard|pharyngitis)\b", "sore throat"),
    # Weight loss
    (r"\b(weight\s*loss|wasting|weight\s*kam\s*hona)\b", "weight loss"),
    # High blood pressure symptoms
    (r"\b(high\s*(?:blood\s*)?pressure|hypertension)\b", "high blood pressure"),
    # Low blood sugar
    (r"\b(low\s*sugar|hypogly?caemia|sugar\s*drop)\b", "hypoglycemia"),
]

# Urgency keywords → urgency flag name
_URGENCY_PATTERNS: list[tuple[str, str]] = [
    (r"\b(chest\s*pain|seena\s*dard)\b", "chest_pain"),
    (r"\b(breath(?:less(?:ness)?)?|difficulty\s*breath(?:ing)?|sans\s*lene\s*mein\s*takleef|shortness\s*of\s*breath)\b", "difficulty_breathing"),
    (r"\b(unconscious|unresponsive|behosh)\b", "unconscious"),
    (r"\b(convulsion|seizure|fit)\b", "seizure"),
    (r"\b(snake\s*bite|snakebite)\b", "snake_bite"),
    (r"\b(very\s*high\s*fever|>104|104\s*f|tez\s*bukhaar)\b", "high_fever"),
    (r"\b(heavy\s*bleeding|severe\s*bleed|haemorrhage)\b", "severe_bleeding"),
    (r"\b(can[' ]?t\s*walk|unable\s*to\s*walk|can[' ]?t\s*stand)\b", "unable_to_walk"),
    (r"\b(confusion|disoriented|altered\s*consciousness)\b", "altered_consciousness"),
    (r"\b(severe\s*abdominal\s*pain|acute\s*abdomen)\b", "severe_abdominal_pain"),
    (r"\b(trauma|accident|injury|fracture)\b", "trauma"),
]

# Duration extraction patterns
_DURATION_PATTERNS: list[tuple[str, int | None]] = [
    # "for X days / din se"
    (r"(?:for\s*)?(\d+)\s*(?:days?|din(?:\s*se)?)", None),     # None = multiplier×1
    (r"(?:for\s*)?(\d+)\s*weeks?", 7),
    (r"(?:for\s*)?(\d+)\s*months?", 30),
    # Hinglish
    (r"(\d+)\s*hafte\s*se", 7),
    (r"(\d+)\s*mahine\s*(?:se|bhar\s*se)?", 30),
    # Named
    (r"\b(teen|3)\s*din\s*se\b", 3),   # teen din se = 3 days
    (r"\bek\s*hafte\s*se\b", 7),
    (r"\bmahine\s*bhar\s*se\b", 30),
    (r"\bchronic\b", 90),
    (r"\bweek\b", 7),
    (r"\bmonth\b", 30),
]

_SEVERITY_PATTERNS: list[tuple[str, str]] = [
    (r"\b(mild|slight|thoda|thodi\s*si)\b", "mild"),
    (r"\b(severe|very|bahut|tez|intense|acute)\b", "severe"),
    (r"\b(moderate|medium)\b", "moderate"),
]


def _extract_duration(text: str) -> int | None:
    """Pull the first duration mention from text. Returns days."""
    lower = text.lower()
    for pattern, multiplier in _DURATION_PATTERNS:
        m = re.search(pattern, lower)
        if m:
            try:
                n = int(m.group(1))
                return n * (multiplier or 1) if multiplier else n
            except (IndexError, ValueError):
                # Pattern matched as a literal (no capture group for the number)
                try:
                    return int(pattern)  # type: ignore
                except (ValueError, TypeError):
                    # Return the hardcoded value stored as the multiplier
                    return multiplier
    return None


def _regex_extract(text: str) -> tuple[list[ExtractedSymptom], list[str], int | None]:
    """
    Keyword-based fallback extraction. Returns (symptoms, urgency_flags, duration_days).
    All symptoms get confidence=0.6 to signal they came from the regex path.
    """
    lower = text.lower()
    seen: set[str] = set()
    symptoms: list[ExtractedSymptom] = []

    duration_days = _extract_duration(lower)

    # Detect global severity for the whole complaint
    severity: Literal["mild", "moderate", "severe", "unknown"] = "unknown"
    for pat, sev in _SEVERITY_PATTERNS:
        if re.search(pat, lower):
            severity = sev  # type: ignore
            break

    for pattern, name in _SYMPTOM_PATTERNS:
        m = re.search(pattern, lower)
        if m and name not in seen:
            seen.add(name)
            # Try to find a duration close to this symptom mention
            # (simple heuristic: check ±30 chars around the match)
            start = max(0, m.start() - 30)
            end = min(len(lower), m.end() + 30)
            local_dur = _extract_duration(lower[start:end])

            symptoms.append(ExtractedSymptom(
                name=name,
                duration_days=local_dur or duration_days,
                severity=severity,
                confidence=0.6,
                original_phrase=m.group(0),
            ))

    urgency_flags: list[str] = []
    for pattern, flag in _URGENCY_PATTERNS:
        if re.search(pattern, lower) and flag not in urgency_flags:
            urgency_flags.append(flag)

    return symptoms, urgency_flags, duration_days


# ── Extractor class ────────────────────────────────────────────────────────────

class SymptomExtractor:
    """
    LLM-backed extractor. One instance is safe to share across requests
    (AsyncOpenAI client is thread/async-safe).
    """

    def __init__(self, model: str | None = None) -> None:
        self.model = model or os.environ.get("MODEL_NAME", "meta-llama/Llama-3.1-8B-Instruct")
        self._client = AsyncOpenAI(
            api_key=os.environ.get("HF_TOKEN") or os.environ.get("OPENAI_API_KEY", ""),
            base_url=os.environ.get("API_BASE_URL", "https://api-inference.huggingface.co/v1"),
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

        # ── Regex fallback ────────────────────────────────────────────────
        # If the LLM returned nothing useful, extract via keyword matching.
        # Marked with confidence=0.6 so downstream can distinguish LLM vs regex.
        if not symptoms:
            log.info("LLM returned no symptoms — using regex fallback for %r", text[:60])
            symptoms, urgency_flags, complaint_duration_days = _regex_extract(text)
            if symptoms:
                log.info(
                    "Regex fallback extracted %d symptoms: %s",
                    len(symptoms), [s.name for s in symptoms],
                )

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
