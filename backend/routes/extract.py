from __future__ import annotations
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from nlp.extractor import SymptomExtractor
from nlp.matcher import match_complaint
from nlp.auto_migrate import upsert_novel, write_patient_events

router = APIRouter(prefix="/api", tags=["extraction"])
_extractor = SymptomExtractor()

class ExtractRequest(BaseModel):
    text: str
    patient_id: str | None = None

@router.post("/extract")
async def extract(req: ExtractRequest, request: Request):
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="text is required")
    try:
        pool  = request.app.state.pool
        vocab = request.app.state.vocab
        embedder = request.app.state.embedder
        version_id = request.app.state.version_id

        parsed = await _extractor.extract(req.text)
        match_result = await match_complaint(parsed, vocab, pool, embedder)

        if match_result.novel:
            novel_matches = await upsert_novel(
                match_result.novel,
                match_result.embeddings,
                vocab, pool, version_id
            )
            match_result.matched.extend(novel_matches)

        if req.patient_id:
            await write_patient_events(
                req.patient_id, match_result.matched, parsed, pool
            )

        return {
            "raw_text": parsed.raw_text,
            "symptoms": [s.model_dump() for s in parsed.symptoms],
            "matched": [{"symptom_id": m.symptom_id, "name": m.name, "score": m.score, "novel": m.novel} for m in match_result.matched],
            "urgency_flags": parsed.urgency_flags,
            "complaint_duration_days": parsed.complaint_duration_days,
            "model_used": parsed.model_used,
            "parse_ms": parsed.parse_ms,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
