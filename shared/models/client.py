"""
shared/models/client.py — Client (tenant) model.

Table: public.clients

Fields:
    id, name, slug, schema_name, industry,
    allowed_domains (JSONB), allowed_ips (JSONB), is_active

This is a global table — exists in the public schema.
Each client maps to a tenant schema: tenant_<slug>.
"""
