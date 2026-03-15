# COPILOT_INSTRUCTIONS.md

## Context

Minerva is a multi-tenant AI platform.
Hierarchy: Organization -> Businesses -> Users / Sessions.

Isolation: Schema-per-business (tenant_<business_slug>).
Global data: public schema (Organizations, Businesses, Users).

## Data Model Rules

-   When writing SQL, always distinguish between `public` and `tenant` tables.
-   `public.organizations`: Billing entities.
-   `public.businesses`: Tenants. Use `id` (UUID) or `slug` (text).
-   `tenant_xxxx.sessions`: Conversations.
-   `tenant_xxxx.business_configs`: Per-business settings.
-   Audit columns (`created_on`, `last_updated_on`, etc.) are required on all tables.

## Tenant Routing

-   `TENANT_SCHEMA` environment variable is the source of truth for background tasks.
-   `schema` claim in JWT is the source of truth for Core API requests.
-   Always use `shared/db/tenant_context.py` for routing.

## S3 Pathing

-   Documents: `s3://bucket/businesses/{business_id}/docs/`
-   Vector Indexes: `s3://bucket/businesses/{business_id}/index/`
-   Archives: `s3://bucket/businesses/{business_id}/archives/{job_id}/`

## Coding Style

-   Use `async/await` for all I/O.
-   Use `shared/models/` for data access.
-   Use `shared/utils/logging.py` for all logging.
-   Follow the Pipeline Component pattern for Core logic.
-   Configuration is accessed via `ConfigCache` singleton.

## Troubleshooting

-   If a tenant schema is missing, check the `public.businesses` table.
-   If RAG results are stale, check if NOTIFY `index_updates` was sent.
-   Always check `ingestion_jobs` for pipeline failures.
