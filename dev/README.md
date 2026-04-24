# dev/ — Test & tooling scaffold

Everything in this folder is for development, verification, and performance
checks. **It is not required at runtime.** When the environment is ready to
deploy, delete the whole folder — nothing under `rural_doc_env/`, `server/`,
`scripts/`, or `migrations/` imports from here.

## Contents

| File | Purpose |
|------|---------|
| `check_db.py` | Smoke test: verifies `.env` loads, Supabase is reachable, expected tables exist, pgvector is enabled. |
| `perf_test.py` | 10-episode end-to-end run with an informed-random policy. Writes Layer 4 rows, measures step + persist latency, emits a JSON report to `dev/runs/`. |
| `validate_env.py` | Pre-submission checklist over scenarios, models, tools, rewards, progression — pure in-process checks, no DB. |
| `validate_cli.py` | Thin CLI wrapper around `validate_env.py`. |
| `runs/` | JSON perf reports, timestamped. |

## Running

All commands from the repo root:

```bash
python dev/check_db.py
python dev/perf_test.py --n 10 --agent-version random_v0 --seed 42
python dev/validate_cli.py
```

## Deploy day

```bash
rm -rf dev/
```

That's it. Nothing else will break.
