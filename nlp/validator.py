"""
nlp/validator.py — schema enforcement + recovery for LLM extraction output.

Stage 3 of the unstructured-input pipeline:

    LLMResponse  ─►  validate_and_recover()  ─►  ParsedComplaint

Three layers, in order:

  1. Pydantic parse against ParsedComplaint / ExtractedSymptom.
     If it works, we're done.
  2. Forgiving normalisation — coerce common LLM shape mistakes
     ("severity: high" → "severe", missing fields → defaults,
     duration as "3 days" string → 3 int) and re-validate.
  3. One re-prompt to the LLM with the validation error message
     attached. Returns whatever the second attempt yields.

If ALL three fail, returns None — the caller is expected to fall back
to the regex extractor in nlp.extractor (which doesn't go through this
path because it can't fail validation by construction).

WHY A SEPARATE MODULE
---------------------
Coupling validation with the LLM client made the latter hard to swap.
Keeping it standalone lets the GRPO trainer reuse it as a reward signal:
"reward = 1 if validate succeeds without recovery, 0.5 if normalisation
fixed it, 0 if even the re-prompt failed".
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import ValidationError

from nlp.extractor import ExtractedSymptom, ParsedComplaint
from nlp.llm_client import LLMResponse, OllamaClient

log = logging.getLogger("ruraldoc.nlp.validator")


# ── Public API ────────────────────────────────────────────────────────────────


async def validate_and_recover(
    llm_resp: LLMResponse,
    *,
    raw_text: str,
    messages: list[dict[str, str]],
    llm: OllamaClient,
    allow_reprompt: bool = True,
) -> tuple[ParsedComplaint | None, str]:
    """
    Try to turn an LLM response into a ParsedComplaint.

    Returns (parsed_or_none, status) where status is one of:
        "ok"            — clean parse, no recovery needed
        "normalised"    — coerced into shape after pydantic failure
        "reprompted"    — needed a second LLM call
        "failed"        — could not produce a valid object
    """
    # ── Layer 1: direct parse ───────────────────────────────────────────
    if llm_resp.json_obj is not None:
        try:
            parsed = _to_parsed_complaint(
                llm_resp.json_obj,
                raw_text=raw_text,
                model=llm_resp.model,
                parse_ms=llm_resp.parse_ms,
            )
            return parsed, "ok"
        except ValidationError as ve:
            log.info("LLM JSON failed strict validation, attempting normalisation: %s",
                     str(ve)[:200])
        except Exception as exc:
            log.warning("Unexpected validation error: %s", exc)

    # ── Layer 2: normalise + retry ──────────────────────────────────────
    if llm_resp.json_obj is not None:
        normalised = _normalise(llm_resp.json_obj)
        try:
            parsed = _to_parsed_complaint(
                normalised,
                raw_text=raw_text,
                model=llm_resp.model,
                parse_ms=llm_resp.parse_ms,
            )
            return parsed, "normalised"
        except ValidationError as ve:
            log.info("Normalisation didn't fix it: %s", str(ve)[:200])

    # ── Layer 3: re-prompt with the error message ───────────────────────
    if allow_reprompt:
        retry = await _reprompt(
            llm=llm,
            messages=messages,
            previous_text=llm_resp.raw_text,
        )
        if retry.json_obj is not None:
            try:
                parsed = _to_parsed_complaint(
                    _normalise(retry.json_obj),
                    raw_text=raw_text,
                    model=retry.model,
                    parse_ms=llm_resp.parse_ms + retry.parse_ms,
                )
                return parsed, "reprompted"
            except ValidationError as ve:
                log.warning("Re-prompt still failed validation: %s", str(ve)[:200])

    return None, "failed"


# ── Internals ─────────────────────────────────────────────────────────────────


_VALID_SEVERITY = {"mild", "moderate", "severe", "unknown"}

# Common LLM mistakes → canonical severity
_SEVERITY_ALIASES = {
    "low": "mild",
    "minor": "mild",
    "slight": "mild",
    "medium": "moderate",
    "med": "moderate",
    "high": "severe",
    "very": "severe",
    "very severe": "severe",
    "intense": "severe",
    "acute": "severe",
    "critical": "severe",
    "": "unknown",
    "none": "unknown",
    "n/a": "unknown",
    None: "unknown",
}


def _to_parsed_complaint(
    obj: dict[str, Any],
    *,
    raw_text: str,
    model: str,
    parse_ms: int,
) -> ParsedComplaint:
    """Strict pydantic conversion. Will raise ValidationError on bad shape."""
    return ParsedComplaint(
        raw_text=raw_text,
        symptoms=[ExtractedSymptom(**s) for s in obj.get("symptoms", [])],
        urgency_flags=list(obj.get("urgency_flags", []) or []),
        complaint_duration_days=_coerce_int(obj.get("complaint_duration_days")),
        model_used=model,
        parse_ms=parse_ms,
    )


def _normalise(obj: dict[str, Any]) -> dict[str, Any]:
    """
    Coerce commonly-mangled fields into the strict schema. Non-mutating —
    returns a new dict so the original LLM payload is preserved for logs.
    """
    out: dict[str, Any] = {}

    # symptoms[]
    raw_syms = obj.get("symptoms")
    if not isinstance(raw_syms, list):
        raw_syms = []
    syms_out: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    for s in raw_syms:
        if not isinstance(s, dict):
            continue
        name = (s.get("name") or "").strip().lower()
        if not name or name in seen_names:
            continue
        seen_names.add(name)

        sev_raw = s.get("severity")
        sev = _normalise_severity(sev_raw)

        conf = s.get("confidence")
        try:
            conf_f = float(conf) if conf is not None else 1.0
        except (TypeError, ValueError):
            conf_f = 1.0
        conf_f = max(0.0, min(1.0, conf_f))

        syms_out.append({
            "name": name,
            "duration_days": _coerce_int(s.get("duration_days")),
            "severity": sev,
            "confidence": conf_f,
            "original_phrase": s.get("original_phrase") or None,
        })
    out["symptoms"] = syms_out

    # urgency_flags
    flags = obj.get("urgency_flags")
    if isinstance(flags, list):
        out["urgency_flags"] = [str(f).strip() for f in flags if f]
    elif isinstance(flags, str):
        # rare: comma-separated string
        out["urgency_flags"] = [t.strip() for t in flags.split(",") if t.strip()]
    else:
        out["urgency_flags"] = []

    out["complaint_duration_days"] = _coerce_int(obj.get("complaint_duration_days"))
    return out


def _normalise_severity(raw: Any) -> str:
    if isinstance(raw, str):
        v = raw.strip().lower()
        if v in _VALID_SEVERITY:
            return v
        return _SEVERITY_ALIASES.get(v, "unknown")
    return _SEVERITY_ALIASES.get(raw, "unknown")  # type: ignore[arg-type]


def _coerce_int(v: Any) -> int | None:
    """Pull an int out of an int / numeric str / "3 days" / None."""
    if v is None:
        return None
    if isinstance(v, bool):
        # bools are ints in Python; reject them explicitly
        return None
    if isinstance(v, (int, float)):
        return int(v) if v >= 0 else None
    if isinstance(v, str):
        s = v.strip().lower()
        if not s or s in {"null", "none", "n/a", "unknown"}:
            return None
        # "3 days", "3", "3.0", "for 3 days"
        digits = ""
        for ch in s:
            if ch.isdigit():
                digits += ch
            elif digits:
                break
        if digits:
            try:
                return int(digits)
            except ValueError:
                return None
    return None


async def _reprompt(
    *,
    llm: OllamaClient,
    messages: list[dict[str, str]],
    previous_text: str,
) -> LLMResponse:
    """
    Append a corrective turn and re-run the model. We keep the original
    system + user turns so the second attempt has full context.
    """
    repair_user = (
        "Your previous response did not match the required schema. "
        "Below is what you returned. Correct it and return ONLY a JSON object "
        "with the exact fields described:\n\n"
        f"{previous_text or '(empty response)'}"
    )
    repaired = list(messages) + [
        {"role": "assistant", "content": previous_text or ""},
        {"role": "user", "content": repair_user},
    ]
    return await llm.chat(repaired, json_mode=True)
