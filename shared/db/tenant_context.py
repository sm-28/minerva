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
