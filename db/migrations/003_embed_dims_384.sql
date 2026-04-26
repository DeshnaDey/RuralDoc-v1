-- ──────────────────────────────────────────────────────────────────────────
-- Migration 003 — switch embedding dimension 1024 → 384
-- ──────────────────────────────────────────────────────────────────────────
-- Why: switching embedder to sentence-transformers/all-MiniLM-L6-v2 for
--      local/offline development (90 MB model, no API key, no HF router
--      permissions needed). all-MiniLM outputs 384-dim vectors; pgvector
--      columns have a fixed dim so we ALTER. Existing rows are not
--      portable across models — TRUNCATE first.
--
-- Model path:
--   Dev:  sentence-transformers/all-MiniLM-L6-v2  (384-dim)  ← this migration
--   Prod: BAAI/bge-large-en-v1.5                  (1024-dim) ← migration 002
--
-- Pre-requisites:
--   Migration 001 (init_schema) must have been applied.
--   Migration 002 may or may not have been applied — this supersedes it for dev.
--
-- Run:
--   psql "$SUPABASE_DB_URL" -f db/migrations/003_embed_dims_384.sql
--   python -m scripts.seed_embeddings
--
-- To go back to 1024-dim (production):
--   psql "$SUPABASE_DB_URL" -f db/migrations/002_embed_dims_1024.sql
--   Set EMBED_MODEL=BAAI/bge-large-en-v1.5 and remove LOCAL_EMBED=1
--   python -m scripts.seed_embeddings
-- ──────────────────────────────────────────────────────────────────────────

begin;

-- Drop ivfflat indexes — tied to column type, must recreate after ALTER.
drop index if exists public.disease_embeddings_embedding_idx;
drop index if exists public.symptom_embeddings_embedding_idx;
drop index if exists public.patient_embeddings_embedding_idx;
drop index if exists public.case_embeddings_embedding_idx;

-- TRUNCATE first: old vectors (1024-dim) can't be cast to 384-dim.
truncate table public.disease_embeddings;
truncate table public.symptom_embeddings;
truncate table public.patient_embeddings;
truncate table public.case_embeddings;

-- ALTER each embedding column to 384-dim.
alter table public.disease_embeddings
  alter column embedding type vector(384);

alter table public.symptom_embeddings
  alter column embedding type vector(384);

alter table public.patient_embeddings
  alter column embedding type vector(384);

alter table public.case_embeddings
  alter column embedding type vector(384);

commit;

-- ──────────────────────────────────────────────────────────────────────────
-- After this migration, reseed:
--
--   LOCAL_EMBED=1 \
--   EMBED_MODEL=sentence-transformers/all-MiniLM-L6-v2 \
--   SUPABASE_DB_URL=<your_url> \
--   python -m scripts.seed_embeddings
--
-- ivfflat indexes (uncomment once you have 100+ rows):
--   create index on public.disease_embeddings
--     using ivfflat (embedding vector_cosine_ops) with (lists = 50);
--   create index on public.symptom_embeddings
--     using ivfflat (embedding vector_cosine_ops) with (lists = 50);
--   create index on public.case_embeddings
--     using ivfflat (embedding vector_cosine_ops) with (lists = 50);
-- ──────────────────────────────────────────────────────────────────────────
