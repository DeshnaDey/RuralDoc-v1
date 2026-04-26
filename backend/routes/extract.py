"""
backend/routes/extract.py — POST /api/extract

Thin wrapper around nlp.pipeline.run(). The route's job is just to:
  • validate the request body
  • pull pool / vocab / embedder / version_id off app.state
  • call pipeline.run() and serialise the result

All real logic — prompt building (Groq), structured extraction (Ollama),
validation, matching, and the Supabase writes — lives in nlp.pipeline.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from nlp.pipeline import PipelineResult, run as run_pipeline

router = APIRouter(prefix="/api", tags=["extraction"])


class PatientMeta(BaseModel):
    age: int | None = None
    gender: str | None = None
    location: str | None = None


class ExtractRequest(BaseModel):
    text: str
    patient_id: str | None = None
    patient_meta: PatientMeta | None = None


@router.post("/extract")
async def extract(req: ExtractRequest, request: Request):
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="text is required")

    try:
        pool = request.app.state.pool
        vocab = request.app.state.vocab
        embedder = request.app.state.embedder
        version_id = request.app.state.version_id

        result: PipelineResult = await run_pipeline(
            req.text,
            pool=pool,
            vocab=vocab,
            embedder=embedder,
            version_id=version_id,
            patient_id=req.patient_id,
            patient_meta=req.patient_meta.model_dump() if req.patient_meta else None,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    parsed = result.parsed
    return {
        "raw_text": parsed.raw_text,
        "symptoms": [s.model_dump() for s in parsed.symptoms],
        "matched": [
            {
                "symptom_id": m.symptom_id,
                "name": m.name,
                "score": m.score,
                "novel": m.novel,
            }
            for m in result.match_result.matched
        ],
        "urgency_flags": parsed.urgency_flags,
        "complaint_duration_days": parsed.complaint_duration_days,
        "model_used": parsed.model_used,
        "parse_ms": parsed.parse_ms,
        # Stage-level audit trail for debugging the pipeline.
        "stages": result.stages,
    }
