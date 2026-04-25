# RuralDoc — Supabase Schema (ER, v1)


- **Hybrid retrieval**: relational FK graph for structured reasoning + `pgvector` embeddings for fuzzy symptom / case similarity.
- **Versioned knowledge layer**: the clinical graph is regenerated on CSV / guideline updates; every scenario and episode pins to a `knowledge_version_id` so training runs remain reproducible.
- **Patient is first-class**: persistent identity across encounters, with a longitudinal history that the agent can condition on and that downstream learning can replay.
- **Event-sourced progression**: patient state per day is folded from ordered events (symptom onset/resolution, vital deltas, lab transitions), with branch conditions so treated vs. untreated trajectories diverge naturally.

The model splits into four layers: **Knowledge**, **Patient & History**, **Scenario + Progression**, **Episode (runtime)**. Each gets its own diagram; a final diagram shows the cross-layer FK edges.

---

## 1. Clinical Knowledge Layer

Sourced from `PHC Disease Guidelines.csv`. Versioned — regenerating rebuilds junction tables under a new `knowledge_version_id` and atomically flips the `is_active` pointer.

```mermaid
erDiagram
    KNOWLEDGE_VERSIONS ||--o{ DISEASES              : "versions"
    KNOWLEDGE_VERSIONS ||--o{ SYMPTOMS              : "versions"
    KNOWLEDGE_VERSIONS ||--o{ TESTS                 : "versions"

    DISEASES           ||--o{ DISEASE_SYMPTOMS      : "presents_with"
    SYMPTOMS           ||--o{ DISEASE_SYMPTOMS      : "seen_in"

    DISEASES           ||--o{ DISEASE_TESTS         : "diagnosed_via"
    TESTS              ||--o{ DISEASE_TESTS         : "used_for"

    DISEASES           ||--o{ DISEASE_DIFFERENTIALS : "mimicked_by"
    DISEASES           ||--o{ DISEASE_DIFFERENTIALS : "mimics"

    DISEASES           ||--o{ DISEASE_VITAL_PATTERNS: "shows"
    VITAL_SIGNS        ||--o{ DISEASE_VITAL_PATTERNS: "measured_in"

    DISEASES           ||--o{ DISEASE_RED_FLAGS     : "warns_of"
    DISEASES           ||--o{ DISEASE_REFERRALS     : "refers_to"
    FACILITIES         ||--o{ DISEASE_REFERRALS     : "receives"

    DISEASES           ||--o| DISEASE_EMBEDDINGS    : "embedded_as"
    SYMPTOMS           ||--o| SYMPTOM_EMBEDDINGS    : "embedded_as"

    KNOWLEDGE_VERSIONS {
        int    id                   PK
        string label
        string source_hash
        bool   is_active
        timestamp created_at
    }
    DISEASES {
        int    id                   PK
        int    version_id           FK
        string name
        string prevalence_text
        string evolution_text
        string red_flags_text
        string icd10
    }
    SYMPTOMS {
        int    id                   PK
        int    version_id           FK
        string name
        string category
    }
    TESTS {
        int    id                   PK
        int    version_id           FK
        string name
        string category
        float  avg_cost_usd
        bool   available_at_phc
    }
    VITAL_SIGNS {
        int    id                   PK
        string name
        string unit
    }
    FACILITIES {
        int    id                   PK
        string name
        string tier
    }
    DISEASE_SYMPTOMS {
        int    disease_id           FK
        int    symptom_id           FK
        string phase
        float  typicality
    }
    DISEASE_TESTS {
        int    disease_id           FK
        int    test_id              FK
        string role
        float  info_gain
    }
    DISEASE_DIFFERENTIALS {
        int    disease_id           FK
        int    mimic_disease_id     FK
        string distinguishing_feature
    }
    DISEASE_VITAL_PATTERNS {
        int    disease_id           FK
        int    vital_id             FK
        string normal_range
        string alarm_range
    }
    DISEASE_RED_FLAGS {
        int    disease_id           FK
        string red_flag_text
        bool   forces_referral
    }
    DISEASE_REFERRALS {
        int    disease_id           FK
        int    facility_id          FK
        string exact_signs
        string do_not_wait_reason
    }
    DISEASE_EMBEDDINGS {
        int    disease_id           PK
        vector embedding
        string text_summary
    }
    SYMPTOM_EMBEDDINGS {
        int    symptom_id           PK
        vector embedding
    }
```

**Regeneration flow** — a nightly (or on-commit) job parses the CSV, diffs against the active version, writes a new `knowledge_versions` row with `is_active=false`, populates all child tables under it, validates (every scenario's `conclusive_test` resolves, every differential points both ways), then atomically flips `is_active`. Scenarios and episodes keep pointing at whichever version they were authored / run under.

---

## 2. Patient & Longitudinal History Layer

Per-patient data the agent should see on each new encounter. This is what makes the RL problem non-Markov in a useful way — a known-diabetic patient's "fatigue + polyuria" should read very differently than a stranger's.

```mermaid
erDiagram
    PATIENTS ||--o{ PATIENT_CONDITIONS       : "has"
    PATIENTS ||--o{ PATIENT_ALLERGIES        : "allergic_to"
    PATIENTS ||--o{ PATIENT_HISTORY_EVENTS   : "logs"
    PATIENTS ||--o{ PATIENT_ENCOUNTERS       : "visits"
    PATIENTS ||--o| PATIENT_EMBEDDINGS       : "embedded_as"

    DISEASES ||--o{ PATIENT_CONDITIONS       : "diagnosed_as"
    DISEASES ||--o{ PATIENT_HISTORY_EVENTS   : "references"
    TESTS    ||--o{ PATIENT_HISTORY_EVENTS   : "references"

    PATIENTS {
        uuid   id                   PK
        jsonb  demographics
        string village_or_region
        timestamp created_at
    }
    PATIENT_CONDITIONS {
        uuid   id                   PK
        uuid   patient_id           FK
        int    disease_id           FK
        date   onset_date
        bool   resolved
        jsonb  notes
    }
    PATIENT_ALLERGIES {
        uuid   id                   PK
        uuid   patient_id           FK
        string substance
        string severity
    }
    PATIENT_HISTORY_EVENTS {
        uuid   id                   PK
        uuid   patient_id           FK
        string event_type
        timestamp event_at
        int    disease_id           FK
        int    test_id              FK
        jsonb  payload
    }
    PATIENT_ENCOUNTERS {
        uuid   id                   PK
        uuid   patient_id           FK
        uuid   episode_id           FK
        timestamp started_at
        timestamp ended_at
        string outcome
    }
    PATIENT_EMBEDDINGS {
        uuid   patient_id           PK
        vector embedding
        string narrative_summary
    }
```

**`patient_history_events`** is the key table — a generic typed event log (`prior_diagnosis`, `test_performed`, `medication_started`, `chronic_flare`, `pregnancy`, etc.) that the agent can query at encounter start. `PATIENT_EMBEDDINGS` lets you retrieve "similar patients" for few-shot context before the first action.

---

## 3. Scenario + Event-Sourced Progression Layer

Scenarios are templates; progression is a stream of events, not day snapshots. To get patient state at day *N* with treatment vector *T*, fold all events where `day_offset ≤ N` and `branch_condition ⊆ T`.

```mermaid
erDiagram
    KNOWLEDGE_VERSIONS ||--o{ SCENARIOS        : "pinned_to"
    DISEASES           ||--o{ SCENARIOS        : "instantiates"
    FACILITIES         ||--o| SCENARIOS        : "refers_to"
    PATIENTS           ||--o{ SCENARIOS        : "templated_for"

    SCENARIOS ||--o{ SCENARIO_TEST_COSTS       : "prices"
    TESTS     ||--o{ SCENARIO_TEST_COSTS       : "costed_in"

    SCENARIOS ||--o{ SCENARIO_RELEVANT_TESTS   : "expects"
    TESTS     ||--o{ SCENARIO_RELEVANT_TESTS   : "relevant_to"

    SCENARIOS ||--o{ SCENARIO_PENALTIES        : "penalizes"

    SCENARIOS ||--o{ PROGRESSION_EVENTS        : "unfolds_as"
    SYMPTOMS  ||--o{ PROGRESSION_EVENTS        : "affects"
    VITAL_SIGNS ||--o{ PROGRESSION_EVENTS      : "affects"
    TESTS     ||--o{ PROGRESSION_EVENTS        : "gated_by"

    SCENARIOS ||--o| CASE_EMBEDDINGS           : "embedded_as"

    SCENARIOS {
        uuid   id                   PK
        int    knowledge_version_id FK
        int    disease_id           FK
        uuid   patient_id           FK
        string difficulty
        float  budget
        int    critical_window_days
        int    referral_facility_id FK
        jsonb  penalty_config
        int    seed
    }
    SCENARIO_TEST_COSTS {
        uuid   scenario_id          FK
        int    test_id              FK
        float  cost
    }
    SCENARIO_RELEVANT_TESTS {
        uuid   scenario_id          FK
        int    test_id              FK
        bool   is_conclusive
    }
    SCENARIO_PENALTIES {
        uuid   scenario_id          FK
        string event_name
        float  reward_delta
    }
    PROGRESSION_EVENTS {
        uuid   id                   PK
        uuid   scenario_id          FK
        int    day_offset
        string event_type
        int    symptom_id           FK
        int    vital_id             FK
        int    test_id              FK
        jsonb  payload
        jsonb  branch_condition
        float  info_gain
        string memory_note
        jsonb  suggests
        jsonb  rules_out
    }
    CASE_EMBEDDINGS {
        uuid   scenario_id          PK
        vector embedding
        string narrative
    }
```

**`event_type` examples**: `symptom_onset`, `symptom_resolved`, `vital_shift`, `test_becomes_positive`, `status_transition`, `penalty_event`. **`branch_condition`** is a JSONB predicate like `{"treated_with": "artemisinin", "before_day": 4}` — the fold skips events whose conditions aren't met by the current episode state. This cleanly supports "untreated malaria spikes fevers" vs. "treated malaria resolves by day 3" without duplicating rows.

---

## 4. Episode (Runtime) Layer

What the RL loop actually writes. Keep this thin and append-only — it's your offline-RL goldmine.

```mermaid
erDiagram
    SCENARIOS ||--o{ EPISODES         : "instantiated_as"
    EPISODES  ||--o{ EPISODE_STEPS    : "comprises"
    EPISODES  ||--o| PATIENT_ENCOUNTERS: "recorded_as"

    EPISODES {
        uuid   id                   PK
        uuid   scenario_id          FK
        int    knowledge_version_id FK
        string agent_version
        timestamp started_at
        timestamp ended_at
        string final_diagnosis
        bool   referred
        string outcome
        float  total_reward
    }
    EPISODE_STEPS {
        uuid   id                   PK
        uuid   episode_id           FK
        int    step_num
        int    day
        string action_type
        jsonb  action_payload
        jsonb  observation
        float  reward
        float  cumulative_reward
        jsonb  folded_state
    }
```

`folded_state` caches the event-fold output at each step — useful for debugging and for offline RL without re-folding. `knowledge_version_id` on `EPISODES` lets you compare policies fairly across guideline updates.

---

## 5. Cross-Layer FK Overview

The edges that actually matter for agent traversal:

```mermaid
erDiagram
    KNOWLEDGE_VERSIONS ||--o{ DISEASES     : ""
    DISEASES           ||--o{ SCENARIOS    : ""
    PATIENTS           ||--o{ SCENARIOS    : ""
    SCENARIOS          ||--o{ EPISODES     : ""
    EPISODES           ||--o{ EPISODE_STEPS: ""
    PATIENTS           ||--o{ PATIENT_ENCOUNTERS : ""
    EPISODES           ||--o| PATIENT_ENCOUNTERS : ""
    SCENARIOS          ||--o{ PROGRESSION_EVENTS : ""
    DISEASES           ||--o{ PATIENT_HISTORY_EVENTS : ""

    KNOWLEDGE_VERSIONS { int id PK }
    DISEASES           { int id PK }
    PATIENTS           { uuid id PK }
    SCENARIOS          { uuid id PK }
    EPISODES           { uuid id PK }
    EPISODE_STEPS      { uuid id PK }
    PROGRESSION_EVENTS { uuid id PK }
    PATIENT_ENCOUNTERS { uuid id PK }
    PATIENT_HISTORY_EVENTS { uuid id PK }
```

Two paths matter most for the agent's hot query:

1. `EPISODE_STEPS → EPISODE → SCENARIO → DISEASE → DISEASE_SYMPTOMS / DISEASE_TESTS` — structured reasoning over the current case.
2. `EPISODE_STEPS → EPISODE → SCENARIO → PATIENT → PATIENT_HISTORY_EVENTS` — personalization / prior-visit context.

Vector lookups happen in parallel: `SYMPTOM_EMBEDDINGS` for fuzzy symptom matching, `CASE_EMBEDDINGS` for few-shot retrieval of similar scenarios, `PATIENT_EMBEDDINGS` for similar-patient retrieval.

---

## Open design questions before writing SQL

1. **Patient reuse across scenarios** — should the same `patient_id` appear in multiple scenarios (recurring patients, longitudinal learning) or is every scenario a fresh synthetic patient? Affects uniqueness constraints on `SCENARIOS.patient_id`.
2. **Progression branch vocabulary** — what's the closed set of keys allowed in `branch_condition` JSONB (`treated_with`, `referred_by_day`, `budget_below`, etc.)? I'd rather define this upfront than let it sprawl.
3. **Embedding generation** — generated offline in a worker, or at write time via a Supabase edge function? And which model?
4. **Knowledge-version retention** — keep forever for reproducibility, or rolling window of last N versions?

If those answers are straightforward, next step is the CREATE TABLE migration + seed script from the CSV.
