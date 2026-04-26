"""
nlp/pipeline.py — single entry point for the unstructured-input flow.

Architecture:
    raw text
        ▼
    PromptBuilder (Groq)              ── stage 1: cleanup + context hint
        ▼
    OllamaClient.chat()               ── stage 2: structured extraction
        ▼
    validate_and_recover()            ── stage 3: pydantic + recovery
        ▼
    [regex fallback if LLM returned nothing]   ── stage 3b: safety net
        ▼
    match_complaint()                 ── stage 4: vocab/pgvector match
        ▼
    upsert_novel() + write_patient_events()    ── stage 5: Supabase write
        ▼
    PipelineResult


WHY THIS LIVES IN A SINGLE MODULE
---------------------------------
The previous extract route stitched extractor / matcher / auto_migrate
inline. That made it impossible to reuse the flow from a script (e.g.
seeding past complaints) and impossible to swap the LLM transport without
touching the route. With pipeline.run() the route is a thin wrapper and
the same function is used by:
  • backend/routes/extract.py        (live API)
  • scripts/seed_nlp_test.py         (smoke / regression)
  • future GRPO trainer              (synthetic complaint generation)

GRACEFUL DEGRADATION CHAIN
--------------------------
If the LLM is unavailable (Ollama not running) we skip stages 1-3 and go
straight to the regex extractor. That keeps /api/extract responsive even
on a laptop without a model server, which matches the "feel free to make
changes" guidance about not blocking the rest of the dev loop on Ollama.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from nlp.auto_migrate import upsert_novel, write_patient_events
from nlp.extractor import ExtractedSymptom, ParsedComplaint, _regex_extract
from nlp.llm_client import OllamaClient, ollama_client
from nlp.matcher import MatchResult, match_complaint
from nlp.prompt_builder import BuiltPrompt, PromptBuilder, prompt_builder
from nlp.validator import validate_and_recover
from nlp.vocab import SymptomMatch, SymptomVocab
from rag.embeddings import Embedder

log = logging.getLogger("ruraldoc.nlp.pipeline")


# ── Result type ───────────────────────────────────────────────────────────────


@dataclass
class PipelineResult:
    """
    Full audit trail for one /api/extract call.

    parsed       : final ParsedComplaint (LLM or regex)
    match_result : matcher output (matched + novel + embeddings)
    novel_added  : SymptomMatches inserted by upsert_novel (subset of matched)
    stages       : per-stage timings + status — surfaces in API response
                   so the frontend / debug UI can show exactly what ran.
    """
    parsed: ParsedComplaint
    match_result: MatchResult
    novel_added: list[SymptomMatch] = field(default_factory=list)
    stages: dict[str, Any] = field(default_factory=dict)


# ── Orchestrator ──────────────────────────────────────────────────────────────


async def run(
    text: str,
    *,
    pool,
    vocab: SymptomVocab,
    embedder: Embedder,
    version_id: int,
    patient_id: str | None = None,
    patient_meta: dict | None = None,
    builder: PromptBuilder | None = None,
    llm: OllamaClient | None = None,
) -> PipelineResult:
    """
    Run the full unstructured-input pipeline end-to-end.

    Args:
        text          raw complaint string from the patient form
        pool          psycopg async pool
        vocab         loaded SymptomVocab (app.state.vocab)
        embedder      Embedder instance
        version_id    active knowledge_version id
        patient_id    UUID; if provided, we write history events
        patient_meta  optional {"age": ..., "gender": ..., "location": ...}
                      used by the prompt builder for endemic-disease priors
        builder       override the module singleton (testing)
        llm           override the module singleton (testing)

    Returns:
        PipelineResult — never raises on LLM failure; the regex fallback
        guarantees we always return *something* parseable.
    """
    builder = builder or prompt_builder
    llm = llm or ollama_client
    stages: dict[str, Any] = {}

    # ── Stage 1: prompt building ─────────────────────────────────────────
    t0 = time.monotonic()
    built: BuiltPrompt = await builder.build(text, patient_meta=patient_meta)
    stages["prompt_builder"] = {
        "ms": int((time.monotonic() - t0) * 1000),
        **built.meta,
        "language": built.language,
        "hint_category": built.hint_category,
    }

    parsed: ParsedComplaint | None = None
    extraction_status = "skipped"

    # ── Stages 2 + 3: LLM + validation ───────────────────────────────────
    t1 = time.monotonic()
    llm_resp = await llm.chat(built.messages, json_mode=True)
    if llm_resp.error:
        stages["llm"] = {
            "ms": int((time.monotonic() - t1) * 1000),
            "model": llm_resp.model,
            "error": llm_resp.error,
        }
    else:
        parsed, extraction_status = await validate_and_recover(
            llm_resp,
            raw_text=text,
            messages=built.messages,
            llm=llm,
        )
        stages["llm"] = {
            "ms": int((time.monotonic() - t1) * 1000),
            "model": llm_resp.model,
            "status": extraction_status,
            "raw_chars": len(llm_resp.raw_text),
        }

    # ── Stage 3b: regex fallback ─────────────────────────────────────────
    if parsed is None or not parsed.symptoms:
        t2 = time.monotonic()
        symptoms, urgency_flags, duration = _regex_extract(text)
        stages["regex_fallback"] = {
            "ms": int((time.monotonic() - t2) * 1000),
            "fired": True,
            "symptom_count": len(symptoms),
        }
        # Merge: keep any LLM symptoms we did get; regex tops up the rest.
        if parsed is None:
            parsed = ParsedComplaint(
                raw_text=text,
                symptoms=symptoms,
                urgency_flags=urgency_flags,
                complaint_duration_days=duration,
                model_used=llm.model + "+regex",
                parse_ms=stages["llm"].get("ms", 0) + stages["regex_fallback"]["ms"],
            )
        else:
            existing = {s.name for s in parsed.symptoms}
            parsed.symptoms.extend(s for s in symptoms if s.name not in existing)
            for f in urgency_flags:
                if f not in parsed.urgency_flags:
                    parsed.urgency_flags.append(f)
            if parsed.complaint_duration_days is None:
                parsed.complaint_duration_days = duration
    else:
        stages["regex_fallback"] = {"fired": False}

    # ── Stage 4: matcher ─────────────────────────────────────────────────
    t3 = time.monotonic()
    match_result = await match_complaint(parsed, vocab, pool, embedder)
    stages["matcher"] = {
        "ms": int((time.monotonic() - t3) * 1000),
        "matched": len(match_result.matched),
        "novel": len(match_result.novel),
    }

    # ── Stage 5: Supabase migrate + events ───────────────────────────────
    t4 = time.monotonic()
    novel_added: list[SymptomMatch] = []
    if match_result.novel:
        novel_added = await upsert_novel(
            match_result.novel,
            match_result.embeddings,
            vocab,
            pool,
            version_id,
        )
        match_result.matched.extend(novel_added)

    if patient_id and (match_result.matched or parsed.symptoms):
        try:
            await write_patient_events(patient_id, match_result.matched, parsed, pool)
        except Exception as exc:
            log.warning("write_patient_events failed (non-fatal): %s", exc)

    stages["migrate_supabase"] = {
        "ms": int((time.monotonic() - t4) * 1000),
        "novel_inserted": len(novel_added),
        "patient_events_written": bool(patient_id and match_result.matched),
    }

    return PipelineResult(
        parsed=parsed,
        match_result=match_result,
        novel_added=novel_added,
        stages=stages,
    )
