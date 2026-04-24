"""
db — Async database connectivity for RuralDocEnv (Supabase / psycopg3).

Quick usage:
    from db import get_conn

    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT 1")
"""

from db.pool import get_conn, get_pool, close_pool
from db.settings import settings

__all__ = ["get_conn", "get_pool", "close_pool", "settings"]
