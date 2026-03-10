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
