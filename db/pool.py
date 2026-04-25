"""
db/pool.py — Async psycopg3 connection pool, one per process.

Why a pool: FastAPI handles requests concurrently (and the eventual UI will
fire multiple rollouts in parallel). A singleton AsyncConnectionPool hands
out pre-warmed connections without reconnecting on every query.

Lifecycle:
    * get_pool() lazily opens the pool on first call.
    * close_pool() should be called on server shutdown (FastAPI lifespan).
    * get_conn() is the common entry point — yields a connection in a
      context manager that returns it to the pool on exit.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from db.settings import settings


_pool: AsyncConnectionPool | None = None


async def get_pool() -> AsyncConnectionPool:
    """Return the singleton pool, opening it on first call."""
    global _pool
    if _pool is None:
        _pool = AsyncConnectionPool(
            conninfo=settings.supabase_db_url,
            min_size=settings.pool_min_size,
            max_size=settings.pool_max_size,
            open=False,
            # Supabase closes idle connections after ~10 min; recycle earlier.
            max_idle=300,
            # Transaction pooler (:6543) multiplexes backends and doesn't
            # support prepared-statement reuse — disable them.
            kwargs={"prepare_threshold": None},
        )
        await _pool.open()
    return _pool


async def close_pool() -> None:
    """Close the pool. Safe to call multiple times."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


@asynccontextmanager
async def get_conn() -> AsyncIterator[AsyncConnection]:
    """
    Async context manager that yields a pooled AsyncConnection.

    Example:
        async with get_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1;")
    """
    pool = await get_pool()
    async with pool.connection() as conn:
        yield conn
