"""
shared/db/connection.py — Database connection pool (Singleton).

Purpose:
    Manages the PostgreSQL connection pool shared across all requests
    within a single process.

Pattern:
    Singleton — one connection pool per process.

Methods:
    get_pool() → asyncpg.Pool or SQLAlchemy engine
    get_connection(tenant_schema: str) → connection with schema set

Notes:
    - Connection pool is initialised once at service startup.
    - The tenant schema is set via SET search_path at the start of
      each request/transaction.
    - Pool size should be tuned based on ECS task count and RDS limits.
"""

import asyncio
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import asyncpg

from shared.utils.logging import get_logger

logger = get_logger("shared.db.connection")

_pool: asyncpg.Pool | None = None
_pool_lock = asyncio.Lock()


async def get_pool() -> asyncpg.Pool:
    """
    Return the process-level connection pool, creating it on first call.

    Reads connection parameters from environment variables:
        DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
        DB_POOL_MIN_SIZE (default: 2)
        DB_POOL_MAX_SIZE (default: 10)

    Returns:
        asyncpg.Pool — the shared connection pool.
    """
    global _pool
    if _pool is not None:
        return _pool

    async with _pool_lock:
        # Double-checked locking
        if _pool is not None:
            return _pool

        dsn = _build_dsn()
        min_size = int(os.getenv("DB_POOL_MIN_SIZE", "2"))
        max_size = int(os.getenv("DB_POOL_MAX_SIZE", "10"))

        logger.info(
            "Initialising database connection pool",
            extra={"min_size": min_size, "max_size": max_size},
        )

        _pool = await asyncpg.create_pool(
            dsn=dsn,
            min_size=min_size,
            max_size=max_size,
            command_timeout=30,
        )
        logger.info("Database connection pool ready.")
    return _pool


@asynccontextmanager
async def get_connection(tenant_schema: str | None = None) -> AsyncGenerator[asyncpg.Connection, None]:
    """
    Async context manager that yields a connection with the tenant schema set.

    Args:
        tenant_schema: PostgreSQL schema name (e.g. 'tenant_acme').
                       If None, search_path remains at the pool default.

    Usage:
        async with get_connection("tenant_acme") as conn:
            rows = await conn.fetch("SELECT * FROM documents")
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        if tenant_schema:
            await conn.execute(f"SET search_path TO {tenant_schema}, public")
        try:
            yield conn
        finally:
            # Reset search_path so the connection is safe to return to pool
            await conn.execute("SET search_path TO public")


async def close_pool() -> None:
    """Close the connection pool gracefully. Call at process shutdown."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("Database connection pool closed.")


# ── Internal helpers ──────────────────────────────────────────────────────────

def _build_dsn() -> str:
    """Construct the PostgreSQL DSN from environment variables."""
    host = os.environ["DB_HOST"]
    port = os.getenv("DB_PORT", "5432")
    name = os.environ["DB_NAME"]
    user = os.environ["DB_USER"]
    password = os.environ["DB_PASSWORD"]
    return f"postgresql://{user}:{password}@{host}:{port}/{name}"
