-- RuralDoc initial schema — v1 (2026-04-21)
-- Maps the ER diagram in schema_ER_v1.md to Supabase/Postgres.
-- Safe to run once on an empty schema. Wrapped in a transaction so a failure
-- leaves no partial state. If you need to re-run during dev, drop the schema
-- first (see bottom of file for a teardown block, kept commented out).
--
-- Conventions:
--   * All tables live in `public` (Supabase default). Move to a dedicated
--     schema (e.g. `ruraldoc`) if you prefer tighter RLS separation.
--   * pgvector uses 1536 dims (OpenAI text-embedding-3-small / ada-002).
--     Change the `vector(1536)` size if you pick a different model.
--   * RLS is enabled on every table with a permissive service_role policy.
--     Tighten before exposing anon/authenticated roles to the client.
--   * Every table has updated_at with a shared trigger.

begin;

-- ──────────────────────────────────────────────────────────────────────────
-- 0. Extensions
-- ──────────────────────────────────────────────────────────────────────────
create extension if not exists "pgcrypto";   -- gen_random_uuid()
create extension if not exists "vector";     -- pgvector (Supabase: enable via dashboard if this errors)

-- Shared updated_at trigger fn
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end $$;

-- ──────────────────────────────────────────────────────────────────────────
-- 1. Knowledge versioning
-- ──────────────────────────────────────────────────────────────────────────
create table public.knowledge_versions (
  id           bigint generated always as identity primary key,
  label        text not null,
  source_hash  text,                          -- sha of the CSV / guideline blob
  is_active    boolean not null default false,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);
create unique index knowledge_versions_active_uniq
  on public.knowledge_versions (is_active) where is_active;

-- ──────────────────────────────────────────────────────────────────────────
-- 2. Knowledge layer (vocabularies)
-- ──────────────────────────────────────────────────────────────────────────
create table public.diseases (
  id                bigint generated always as identity primary key,
  version_id        bigint not null references public.knowledge_versions(id) on delete cascade,
  name              text not null,
  prevalence_text   text,
  evolution_text    text,
  red_flags_text    text,
  icd10             text,
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now(),
  unique (version_id, name)
);

create table public.symptoms (
  id          bigint generated always as identity primary key,
  version_id  bigint not null references public.knowledge_versions(id) on delete cascade,
  name        text not null,
  category    text,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  unique (version_id, name)
);

create table public.tests (
  id                 bigint generated always as identity primary key,
  version_id         bigint not null references public.knowledge_versions(id) on delete cascade,
  name               text not null,
  category           text,
  avg_cost_usd       numeric(10,2),
  available_at_phc   boolean not null default true,
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now(),
  unique (version_id, name)
);

create table public.vital_signs (
  id         bigint generated always as identity primary key,
  name       text not null unique,
  unit       text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.facilities (
  id         bigint generated always as identity primary key,
  name       text not null,
  tier       text check (tier in ('PHC','District','Secondary','Tertiary','Surgical','Specialty')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- ──────────────────────────────────────────────────────────────────────────
-- 3. Knowledge junction tables (the FK graph)
-- ──────────────────────────────────────────────────────────────────────────
create table public.disease_symptoms (
  disease_id  bigint not null references public.diseases(id) on delete cascade,
  symptom_id  bigint not null references public.symptoms(id) on delete cascade,
  phase       text check (phase in ('classic','early','late','critical')),
  typicality  numeric(3,2) check (typicality between 0 and 1),
  primary key (disease_id, symptom_id, phase)
);
create index on public.disease_symptoms (symptom_id);

create table public.disease_tests (
  disease_id bigint not null references public.diseases(id) on delete cascade,
  test_id    bigint not null references public.tests(id) on delete cascade,
  role       text not null check (role in ('first_line','second_line','conclusive','cost_efficient_combo')),
  info_gain  numeric(3,2) check (info_gain between 0 and 1),
  primary key (disease_id, test_id, role)
);
create index on public.disease_tests (test_id);

create table public.disease_differentials (
  disease_id              bigint not null references public.diseases(id) on delete cascade,
  mimic_disease_id        bigint not null references public.diseases(id) on delete cascade,
  distinguishing_feature  text,
  primary key (disease_id, mimic_disease_id),
  check (disease_id <> mimic_disease_id)
);
create index on public.disease_differentials (mimic_disease_id);

create table public.disease_vital_patterns (
  disease_id   bigint not null references public.diseases(id) on delete cascade,
  vital_id     bigint not null references public.vital_signs(id) on delete cascade,
  normal_range text,
  alarm_range  text,
  primary key (disease_id, vital_id)
);

create table public.disease_red_flags (
  id              bigint generated always as identity primary key,
  disease_id      bigint not null references public.diseases(id) on delete cascade,
  red_flag_text   text not null,
  forces_referral boolean not null default true
);
create index on public.disease_red_flags (disease_id);

create table public.disease_referrals (
  disease_id        bigint not null references public.diseases(id) on delete cascade,
  facility_id       bigint not null references public.facilities(id) on delete cascade,
  exact_signs       text,
  do_not_wait_reason text,
  primary key (disease_id, facility_id)
);

-- ──────────────────────────────────────────────────────────────────────────
-- 4. Embeddings (pgvector)
-- ──────────────────────────────────────────────────────────────────────────
create table public.disease_embeddings (
  disease_id    bigint primary key references public.diseases(id) on delete cascade,
  embedding     vector(1536) not null,
  text_summary  text,
  updated_at    timestamptz not null default now()
);

create table public.symptom_embeddings (
  symptom_id  bigint primary key references public.symptoms(id) on delete cascade,
  embedding   vector(1536) not null,
  updated_at  timestamptz not null default now()
);

-- ivfflat indexes speed up nearest-neighbour search. Build AFTER you have
-- a few hundred rows — empty-table ivfflat is pointless. Comment these in later.
-- create index on public.disease_embeddings using ivfflat (embedding vector_cosine_ops) with (lists = 50);
-- create index on public.symptom_embeddings using ivfflat (embedding vector_cosine_ops) with (lists = 50);

-- ──────────────────────────────────────────────────────────────────────────
-- 5. Patient & longitudinal history
-- ──────────────────────────────────────────────────────────────────────────
create table public.patients (
  id                uuid primary key default gen_random_uuid(),
  demographics      jsonb not null default '{}'::jsonb,
  village_or_region text,
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now()
);

create table public.patient_conditions (
  id           uuid primary key default gen_random_uuid(),
  patient_id   uuid not null references public.patients(id) on delete cascade,
  disease_id   bigint not null references public.diseases(id) on delete restrict,
  onset_date   date,
  resolved     boolean not null default false,
  notes        jsonb default '{}'::jsonb,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);
create index on public.patient_conditions (patient_id);
create index on public.patient_conditions (disease_id);

create table public.patient_allergies (
  id         uuid primary key default gen_random_uuid(),
  patient_id uuid not null references public.patients(id) on delete cascade,
  substance  text not null,
  severity   text check (severity in ('mild','moderate','severe','anaphylactic')),
  created_at timestamptz not null default now()
);
create index on public.patient_allergies (patient_id);

create table public.patient_history_events (
  id           uuid primary key default gen_random_uuid(),
  patient_id   uuid not null references public.patients(id) on delete cascade,
  event_type   text not null,                 -- prior_diagnosis, test_performed, medication_started, ...
  event_at     timestamptz not null default now(),
  disease_id   bigint references public.diseases(id) on delete set null,
  test_id      bigint references public.tests(id) on delete set null,
  payload      jsonb not null default '{}'::jsonb
);
create index on public.patient_history_events (patient_id, event_at desc);
create index on public.patient_history_events (event_type);

create table public.patient_embeddings (
  patient_id         uuid primary key references public.patients(id) on delete cascade,
  embedding          vector(1536) not null,
  narrative_summary  text,
  updated_at         timestamptz not null default now()
);

-- ──────────────────────────────────────────────────────────────────────────
-- 6. Scenarios + event-sourced progression
-- ──────────────────────────────────────────────────────────────────────────
create table public.scenarios (
  id                    uuid primary key default gen_random_uuid(),
  knowledge_version_id  bigint not null references public.knowledge_versions(id) on delete restrict,
  disease_id            bigint not null references public.diseases(id) on delete restrict,
  patient_id            uuid references public.patients(id) on delete set null,
  difficulty            text check (difficulty in ('easy','medium','hard','expert')),
  budget                numeric(10,2) not null,
  critical_window_days  int not null,
  referral_facility_id  bigint references public.facilities(id) on delete set null,
  penalty_config        jsonb default '{}'::jsonb,
  seed                  bigint,
  created_at            timestamptz not null default now(),
  updated_at            timestamptz not null default now()
);
create index on public.scenarios (disease_id);
create index on public.scenarios (knowledge_version_id);

create table public.scenario_test_costs (
  scenario_id uuid not null references public.scenarios(id) on delete cascade,
  test_id     bigint not null references public.tests(id) on delete restrict,
  cost        numeric(10,2) not null,
  primary key (scenario_id, test_id)
);

create table public.scenario_relevant_tests (
  scenario_id   uuid not null references public.scenarios(id) on delete cascade,
  test_id       bigint not null references public.tests(id) on delete restrict,
  is_conclusive boolean not null default false,
  primary key (scenario_id, test_id)
);

create table public.scenario_penalties (
  id           bigint generated always as identity primary key,
  scenario_id  uuid not null references public.scenarios(id) on delete cascade,
  event_name   text not null,
  reward_delta numeric(6,3) not null
);
create index on public.scenario_penalties (scenario_id);

create table public.progression_events (
  id                uuid primary key default gen_random_uuid(),
  scenario_id       uuid not null references public.scenarios(id) on delete cascade,
  day_offset        int not null,
  event_type        text not null,            -- symptom_onset, symptom_resolved, vital_shift, test_becomes_positive, status_transition, penalty_event
  symptom_id        bigint references public.symptoms(id) on delete set null,
  vital_id          bigint references public.vital_signs(id) on delete set null,
  test_id           bigint references public.tests(id) on delete set null,
  payload           jsonb not null default '{}'::jsonb,
  branch_condition  jsonb not null default '{}'::jsonb,  -- e.g. {"treated_with":"artemisinin","before_day":4}
  info_gain         numeric(3,2),
  memory_note       text,
  suggests          jsonb default '[]'::jsonb,
  rules_out         jsonb default '[]'::jsonb
);
create index on public.progression_events (scenario_id, day_offset);
create index on public.progression_events (event_type);

create table public.case_embeddings (
  scenario_id  uuid primary key references public.scenarios(id) on delete cascade,
  embedding    vector(1536) not null,
  narrative    text,
  updated_at   timestamptz not null default now()
);

-- ──────────────────────────────────────────────────────────────────────────
-- 7. Episode / runtime (append-only RL log)
-- ──────────────────────────────────────────────────────────────────────────
create table public.episodes (
  id                    uuid primary key default gen_random_uuid(),
  scenario_id           uuid not null references public.scenarios(id) on delete restrict,
  knowledge_version_id  bigint not null references public.knowledge_versions(id) on delete restrict,
  agent_version         text,
  started_at            timestamptz not null default now(),
  ended_at              timestamptz,
  final_diagnosis       text,
  referred              boolean,
  outcome               text check (outcome in ('correct','incorrect','referred_correct','referred_incorrect','timeout','error')),
  total_reward          numeric(10,3)
);
create index on public.episodes (scenario_id);
create index on public.episodes (agent_version, started_at desc);

create table public.episode_steps (
  id                uuid primary key default gen_random_uuid(),
  episode_id        uuid not null references public.episodes(id) on delete cascade,
  step_num          int not null,
  day               int not null,
  action_type       text not null check (action_type in ('order_test','diagnose','refer')),
  action_payload    jsonb not null default '{}'::jsonb,
  observation       jsonb not null,
  reward            numeric(10,3) not null,
  cumulative_reward numeric(10,3) not null,
  folded_state      jsonb,                -- cached event-fold at this step
  created_at        timestamptz not null default now(),
  unique (episode_id, step_num)
);
create index on public.episode_steps (episode_id, step_num);

create table public.patient_encounters (
  id         uuid primary key default gen_random_uuid(),
  patient_id uuid not null references public.patients(id) on delete cascade,
  episode_id uuid references public.episodes(id) on delete set null,
  started_at timestamptz not null default now(),
  ended_at   timestamptz,
  outcome    text
);
create index on public.patient_encounters (patient_id, started_at desc);

-- ──────────────────────────────────────────────────────────────────────────
-- 8. updated_at triggers (attach to tables that have the column)
-- ──────────────────────────────────────────────────────────────────────────
do $$
declare t text;
begin
  for t in
    select table_name from information_schema.columns
    where table_schema='public'
      and column_name='updated_at'
      and table_name in (
        'knowledge_versions','diseases','symptoms','tests','vital_signs','facilities',
        'patients','patient_conditions','scenarios',
        'disease_embeddings','symptom_embeddings','patient_embeddings','case_embeddings'
      )
  loop
    execute format(
      'drop trigger if exists set_updated_at on public.%I;
       create trigger set_updated_at before update on public.%I
         for each row execute function public.set_updated_at();', t, t);
  end loop;
end $$;

-- ──────────────────────────────────────────────────────────────────────────
-- 9. RLS — enable everywhere, grant service_role full access.
--     Add anon/authenticated policies before shipping to clients.
-- ──────────────────────────────────────────────────────────────────────────
do $$
declare t text;
begin
  for t in
    select table_name from information_schema.tables
    where table_schema='public' and table_type='BASE TABLE'
  loop
    execute format('alter table public.%I enable row level security;', t);
    execute format(
      'drop policy if exists service_role_all on public.%I;
       create policy service_role_all on public.%I
         as permissive for all to service_role using (true) with check (true);', t, t);
  end loop;
end $$;

commit;

-- ──────────────────────────────────────────────────────────────────────────
-- Teardown (uncomment to wipe; destructive)
-- ──────────────────────────────────────────────────────────────────────────
-- begin;
-- drop table if exists public.patient_encounters, public.episode_steps, public.episodes,
--   public.case_embeddings, public.progression_events, public.scenario_penalties,
--   public.scenario_relevant_tests, public.scenario_test_costs, public.scenarios,
--   public.patient_embeddings, public.patient_history_events, public.patient_allergies,
--   public.patient_conditions, public.patients,
--   public.symptom_embeddings, public.disease_embeddings,
--   public.disease_referrals, public.disease_red_flags, public.disease_vital_patterns,
--   public.disease_differentials, public.disease_tests, public.disease_symptoms,
--   public.facilities, public.vital_signs, public.tests, public.symptoms, public.diseases,
--   public.knowledge_versions cascade;
-- drop function if exists public.set_updated_at();
-- commit;
