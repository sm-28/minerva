"""
dashboard/backend/api/clients.py — Client management endpoints.

Purpose:
    CRUD operations for B2B clients (tenants).

Endpoints:
    POST   /api/v1/admin/clients          — Create a new client and tenant schema
    GET    /api/v1/admin/clients           — List all clients
    GET    /api/v1/admin/clients/{id}      — Get client details
    PUT    /api/v1/admin/clients/{id}      — Update client (name, industry, etc.)
    PATCH  /api/v1/admin/clients/{id}/security — Update allowed_domains, allowed_ips

Notes:
    - Creating a client also creates the tenant schema in PostgreSQL.
    - Domain/IP whitelisting is managed here for auth security.
"""
