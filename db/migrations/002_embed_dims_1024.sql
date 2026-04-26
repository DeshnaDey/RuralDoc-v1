-- ──────────────────────────────────────────────────────────────────────────
-- Migration 002 — switch embedding dimension from 1536 → 1024
-- ──────────────────────────────────────────────────────────────────────────
-- Why: switched embedder from OpenAI text-embedding-3-small (1536d) to
--      BAAI/bge-large-en-v1.5 on HF serverless (1024d). pgvector columns
--      have a fixed dim, so we ALTER. Existing rows are not portable across
--      models — we TRUNCATE and reseed via scripts/seed_embeddings.py.
--
-- Effect: clears all *_embeddings tables and changes their `embedding`
--         column from vector(1536) to vector(1024). Relational data
--         (diseases, symptoms, patients, scenarios) is untouched —
--         only the embedding payloads are dropped.
--
-- Run:  psql "$SUPABASE_DB_URL" -f db/migrations/002_embed_dims_1024.sql
--       python -m scripts.seed_embeddings
-- ──────────────────────────────────────────────────────────────────────────

begin;

-- Drop ivfflat indexes if any were created (they're tied to the column type).
-- Safe even if the indexes don't exist.
drop index if exists public.disease_embeddings_embedding_idx;
drop index if exists public.symptom_embeddings_embedding_idx;
drop index if exists public.patient_embeddings_embedding_idx;
drop index if exists public.case_embeddings_embedding_idx;

-- TRUNCATE first — old vectors are 1536d and can't be cast to 1024d cleanly.
truncate table public.disease_embeddings;
truncate table public.symptom_embeddings;
truncate table public.patient_embeddings;
truncate table public.case_embeddings;

-- ALTER each embedding column to the new dimension.
alter table public.disease_embeddings
  alter column embedding type vector(1024);

alter table public.symptom_embeddings
  alter column embedding type vector(1024);

alter table public.patient_embeddings
  alter column embedding type vector(1024);

alter table public.case_embeddings
  alter column embedding type vector(1024);

-- (Optional) recreate ivfflat indexes after reseeding. Leave commented until
-- you have a few hundred rows — empty-table ivfflat is pointless.
-- create index on public.disease_embeddings using ivfflat (embedding vector_cosine_ops) with (lists = 50);
-- create index on public.symptom_embeddings using ivfflat (embedding vector_cosine_ops) with (lists = 50);
-- create index on public.patient_embeddings using ivfflat (embedding vector_cosine_ops) with (lists = 50);
-- create index on public.case_embeddings   using ivfflat (embedding vector_cosine_ops) with (lists = 50);

commit;

-- ──────────────────────────────────────────────────────────────────────────
-- Reseed step (run from project root):
--     python -m scripts.seed_embeddings
-- This re-embeds every disease, symptom, and (already-seeded) scenario via
-- the new HF-backed Embedder and re-inserts into the *_embeddings tables.
-- ──────────────────────────────────────────────────────────────────────────
