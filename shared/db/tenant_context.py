"""
shared/db/tenant_context.py — Tenant schema routing.

Purpose:
    Provides utilities to set and manage the PostgreSQL search_path
    for tenant isolation. Ensures all queries within a request
    operate against the correct tenant schema.

Methods:
    set_tenant_schema(connection, schema_name: str)
    get_tenant_schema(client_slug: str) → str    (returns 'tenant_<slug>')
    reset_to_public(connection)

Usage:
    Called by the auth middleware after JWT validation to set the
    correct tenant context for the request lifecycle.

Notes:
    - Every database operation within a tenant scope must go through
      a connection that has its search_path set.
    - Global tables (clients, users, system_settings) are accessed
       via the 'public' schema.
"""

import re

import asyncpg


_SLUG_RE = re.compile(r"^[a-z0-9_]+$")


def get_tenant_schema(client_slug: str) -> str:
    """
    Return the PostgreSQL schema name for a given client slug.

    Args:
        client_slug: The client's lowercase URL-safe slug (e.g. 'acme').

    Returns:
        'tenant_<slug>' — e.g. 'tenant_acme'.

    Raises:
        ValueError: If the slug contains characters that could cause SQL injection.
    """
    slug = client_slug.lower().strip()
    if not _SLUG_RE.match(slug):
        raise ValueError(
            f"Invalid client slug '{slug}'. Only lowercase letters, digits, "
            "and underscores are allowed."
        )
    return f"tenant_{slug}"


async def set_tenant_schema(conn: asyncpg.Connection, schema_name: str) -> None:
    """
    Set the PostgreSQL search_path for this connection to the tenant schema.

    Args:
        conn:        An active asyncpg connection.
        schema_name: Target schema name (e.g. 'tenant_acme').
    """
    # Validate schema name to prevent injection
    if not _SLUG_RE.match(schema_name.replace("tenant_", "", 1)):
        raise ValueError(f"Unsafe schema name: '{schema_name}'")
    await conn.execute(f"SET search_path TO {schema_name}, public")


async def reset_to_public(conn: asyncpg.Connection) -> None:
    """
    Reset the search_path back to 'public' (global tables only).

    Args:
        conn: An active asyncpg connection.
    """
    await conn.execute("SET search_path TO public")
