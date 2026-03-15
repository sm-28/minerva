# MINERVA_DEVELOPER_GUIDE.md

## Multi‑Tenancy Strategy

Minerva uses **hierarchical schema‑per‑tenant isolation** at the business level.

-   **Organizations** are top-level billing entities.
-   **Businesses** are autonomous tenants within an organization.
-   Each Business has its own **PostgreSQL schema** (`tenant_<business_slug>`).
-   Each Business has its own **FAISS vector index** stored in S3.
-   Each Business has its own **configuration** in `business_configs`.

### Tenant Routing (Runtime)

The `TENANT_SCHEMA` environment variable is used in ECS tasks (like Ingestion) to lock a process to a specific tenant. In the Core API, the schema is determined from the **JWT token** (the `schema` claim).

All database queries *must* use the `tenant_context` to ensure data isolation. Use `get_connection(schema_name)` to obtain a connection with the correct `search_path`.

------------------------------------------------------------------------

## Database Development

### Shared Ledger (public schema)

-   `organizations`: Global billing entities.
-   `businesses`: Tenant metadata and schema mapping.
-   `users`: Global users with `org_id` and roles (`org_admin`, `business_admin`).
-   `business_api_keys`: Scoped to a specific business.

### Tenant Ledger (`tenant_xxxx` schema)

-   `sessions`, `messages`: Per-business conversation history.
-   `documents`, `ingestion_jobs`: Per-business knowledge base.
-   `business_configs`: Per-business pipeline behavior.

### Migrations

When adding a table to the **tenant schema**, the migration script must iterate through all existing schemas in the `businesses` table to apply the change.

------------------------------------------------------------------------

## Vector Knowledge Base (RAG)

### Ingestion Pipeline

1.  **Dashboard** uploads document to `s3://bucket/businesses/{business_id}/docs/`.
2.  **Ingestion Service** is triggered via ECS.
3.  **Parser** converts file (PDF/Docx/Txt) to raw text.
4.  **Chunker** splits text into chunks (~500 tokens).
5.  **Embedder** generates vectors using the configured model.
6.  **Vector Store** builds a combined FAISS index for the *entire business* (current document + all other active documents).
7.  New index is saved to `s3://bucket/businesses/{business_id}/index/`.
8.  Previous index is archived to `s3://bucket/businesses/{business_id}/archives/{job_id}/`.

### Querying

Core API loads the FAISS index for the business into memory using `ConfigCache`. When a user asks a question, the `rag` component:
1.  Embeds the query.
2.  Performs similarity search against the business's index.
3.  Injects the top-K chunks into the LLM prompt.

------------------------------------------------------------------------

## Configuration & Caching

Minerva avoids Redis to reduce infrastructure complexity. Instead, it uses **in-memory caching** with a periodic refresh from Postgres.

### ConfigCache (shared/config/config_cache.py)

A singleton that holds `business_configs` and `system_settings`.
-   **Loading**: Loads all configs for a `business_id` from the database.
-   **TTL**: Refreshes every 5 minutes.
-   **Invalidation**: Core API exposes an `/internal/cache/refresh` endpoint that can be hit manually (or via NOTIFY when ingestion finishes) to force a reload.

------------------------------------------------------------------------

## Coding Standards

### 1. No Ad-hoc Queries
Always use the models in `shared/models/`. If a complex join is needed, add a method to the model or a utility in `shared/queries/`.

### 2. Graceful Degrations
If a non-critical pipeline component (like goal-steering or feedback) fails, the pipeline *must* continue. Wrap component executions in try-except blocks.

### 3. Async First
Everything in Core and Ingestion should be `async` (using `asyncpg` for DB and `httpx` for API calls).

### 4. Logging
Use `shared/utils/logging.py`. Always include `session_id` or `business_id` in logs where available.

------------------------------------------------------------------------

## Testing

### Unit Tests
Located in `tests/`. Run with `pytest`. Mock all external API calls (OpenAI, Deepgram, etc.) using `pytest-mock` or `respx`.

### Integration Tests
Requires a local Postgres instance. Use `tests/conftest.py` which handles schema creation/cleanup for tests.

```bash
# Run all tests
pytest tests/

# Run specific service tests
pytest tests/core/
```
