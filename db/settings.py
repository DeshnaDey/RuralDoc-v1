"""
db/settings.py — Environment-driven DB configuration.

Reads SUPABASE_DB_URL from .env at project root (or the real environment).
If the var is missing, accessing `settings` will raise — fail-fast beats a
cryptic connection error later.

NOTE: env_file is resolved against the project root (parent of this file's
parent), not the current working directory. This means `python -m
env.inference`, `python scripts/seed_*.py`, and `uvicorn backend.app:app`
all find the same .env regardless of where they're invoked from.
"""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root = parent of db/ — i.e. the directory containing pyproject.toml.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"


class DBSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    supabase_db_url: str = Field(
        ...,
        description=(
            "Supabase Postgres connection URI. Use the pooler URL from "
            "Dashboard → Project Settings → Database → Connection string."
        ),
    )

    # Connection pool sizing. Defaults are fine for dev; tune under real load.
    pool_min_size: int = Field(default=1, ge=0)
    pool_max_size: int = Field(default=10, ge=1)


try:
    settings = DBSettings()  # type: ignore[call-arg]  # env-loaded at import
except Exception as exc:  # pragma: no cover
    # Surface a clear message instead of the raw pydantic ValidationError.
    raise RuntimeError(
        f"DB settings failed to load. Looked for .env at {_ENV_FILE}.\n"
        f"  • Does the file exist? `cp .env.example .env` if not.\n"
        f"  • Is SUPABASE_DB_URL filled in?\n"
        f"Original error: {exc}"
    ) from exc
