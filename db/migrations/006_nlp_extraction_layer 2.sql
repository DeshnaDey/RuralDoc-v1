-- RuralDoc migration 006 — NLP extraction layer (2026-04-25)
--
-- Adds the symptom_extraction_log table that audits every free-text
-- complaint that passes through nlp/extractor.py + nlp/matcher.py.
--
-- Design notes:
--   * raw_text      — the exact string the user typed (immutable audit)
--   * extracted     — JSON array of {name, duration_days, severity, confidence}
--                     as returned by the LLM before DB matching
--   * matched       — JSON array of {symptom_id, name, score, novel}
--                     after SymptomVocab.match(); novel=true means the
--                     symptom was upserted by auto_migrate.py
--   * model_used    — which LLM/embedding model ran (tracks drift over time)
--   * patient_id    — FK to patients; nullable so the log can be written
--                     before the patient row is committed (two-phase flow)
--   * parse_ms      — wall-clock latency for the full extraction round-trip
--
-- The table is append-only by convention. Never UPDATE rows here — if a
-- re-parse is needed, insert a new row and join on the latest created_at.

begin;

create table public.symptom_extraction_log (
  id            uuid primary key default gen_random_uuid(),
  patient_id    uuid references public.patients(id) on delete set null,
  raw_text      text not null,
  extracted     jsonb not null default '[]'::jsonb,   -- LLM output pre-match
  matched       jsonb not null default '[]'::jsonb,   -- post-match with symptom_ids
  urgency_flags jsonb not null default '[]'::jsonb,   -- e.g. ["chest_pain","unconscious"]
  model_used    text,                                  -- e.g. "gpt-4o-mini"
  parse_ms      int,                                   -- round-trip latency
  created_at    timestamptz not null default now()
);

-- Index for patient-centric lookups (PatientDrawer timeline)
create index symptom_extraction_log_patient_idx
  on public.symptom_extraction_log (patient_id, created_at desc);

-- Index to find all extractions that surfaced a specific novel symptom
-- (useful for reviewing auto-migrated vocab)
create index symptom_extraction_log_matched_gin
  on public.symptom_extraction_log using gin (matched);

-- ── RLS ───────────────────────────────────────────────────────────────────
alter table public.symptom_extraction_log enable row level security;
create policy service_role_all on public.symptom_extraction_log
  as permissive for all to service_role using (true) with check (true);

commit;
