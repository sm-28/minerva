"""
dashboard/backend/services/client_service.py — Client management business logic.

Purpose:
    Handles client CRUD operations, tenant schema creation/management,
    and domain/IP whitelist management.

Methods:
    create_client(name, industry, allowed_domains, allowed_ips) → Client
    get_client(client_id) → Client
    list_clients() → list[Client]
    update_client(client_id, updates) → Client
    create_tenant_schema(slug) — Creates the PostgreSQL schema and tables
"""
