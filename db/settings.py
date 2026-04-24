"""
db/settings.py — Environment-driven DB configuration.

Reads SUPABASE_DB_URL from .env at project root (or the real environment).
If the var is missing, accessing `settings` will raise — fail-fast beats a
cryptic connection error later.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DBSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
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


settings = DBSettings()  # type: ignore[call-arg]  # env-loaded at import
