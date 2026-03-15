# MINERVA_DATA_MODEL.md

## Multi‑Tenant Design

Minerva uses a hierarchical multi‑tenant architecture.

Global schema: public (contains Organizations, Businesses, Users)
Tenant schemas: tenant\_\<business_slug\> (contains knowledge base and session data)

------------------------------------------------------------------------

## Audit Columns

All tables must include the following audit columns:

    created_by        UUID
    created_on        TIMESTAMP DEFAULT now()
    last_updated_by   UUID
    last_updated_on   TIMESTAMP DEFAULT now()

These are omitted from individual table definitions below for brevity,
but must be present on every table.

------------------------------------------------------------------------

## Global Tables (Public Schema)

------------------------------------------------------------------------

### organizations

The parent billing and contractual entity.

    id                UUID PK
    name              TEXT NOT NULL
    is_active         BOOLEAN DEFAULT true

------------------------------------------------------------------------

### businesses

An autonomous tenant (or agent) owned by an organization. Each business has its own knowledge base and schema.

    id                UUID PK
    org_id            UUID FK → organizations.id
    name              TEXT NOT NULL
    slug              TEXT UNIQUE NOT NULL
    schema_name       TEXT UNIQUE NOT NULL (tenant_<slug>)
    industry          TEXT
    allowed_domains   JSONB DEFAULT '[]'
    allowed_ips       JSONB DEFAULT '[]'
    is_active         BOOLEAN DEFAULT true

------------------------------------------------------------------------

### business_api_keys

API keys are scoped to a specific business.

    id                    UUID PK
    business_id           UUID FK → businesses.id
    api_key               TEXT UNIQUE NOT NULL
    api_secret_hash       TEXT NOT NULL
    is_active             BOOLEAN DEFAULT true

A business can have a maximum of 2 active api_key pairs at any time.

------------------------------------------------------------------------

### users

    id                UUID PK
    email             TEXT UNIQUE NOT NULL
    name              TEXT
    role              TEXT DEFAULT 'viewer' (org_admin | business_admin | viewer)
    org_id            UUID FK → organizations.id
    is_active         BOOLEAN DEFAULT true

------------------------------------------------------------------------

### user_business_access

Join table for business_admin/viewer access to specific businesses.

    user_id           UUID FK → users.id
    business_id       UUID FK → businesses.id

------------------------------------------------------------------------

### system_settings

    key               TEXT PK
    value             JSONB NOT NULL
    description       TEXT

------------------------------------------------------------------------

## Tenant Tables

All tenant tables exist within the tenant\_\<business_slug\> schema.

------------------------------------------------------------------------

### business_configs (formerly client_configs)

    id                UUID PK
    config_key        TEXT NOT NULL
    config_value      JSONB NOT NULL
    description       TEXT

Common config_keys:

    pipeline_components         — ordered list of active pipeline components
    default_language            — fallback language code (e.g. en-IN)
    goal_definition             — goal type, required fields, completion criteria
    provider_overrides          — per-stage provider selection (e.g. stt: deepgram)
    greeting_template           — initial greeting text template
    unknown_response_template   — response template for unknown queries
    voice_config                — default speaker, pace, language for TTS

------------------------------------------------------------------------

### sessions

    id                    UUID PK
    business_id           UUID FK → businesses.id (denormalized for convenience)
    channel               TEXT (web | whatsapp | phone)
    user_identifier       TEXT
    language              TEXT
    status                TEXT DEFAULT 'active' (active | ended | abandoned)
    conversation_summary  TEXT
    audio_s3_path         TEXT
    goal_state_json       JSONB
    last_activity         TIMESTAMP
    ended_at              TIMESTAMP

------------------------------------------------------------------------

### messages

    id                UUID PK
    session_id        UUID FK → sessions.id
    role              TEXT NOT NULL (user | assistant | system)
    content           TEXT NOT NULL
    audio_s3_path     TEXT
    is_unknown        BOOLEAN DEFAULT false
    rag_context       JSONB

------------------------------------------------------------------------

### documents

    id                UUID PK
    filename          TEXT NOT NULL
    file_type         TEXT DEFAULT 'pdf'
    s3_path           TEXT NOT NULL (s3://bucket/businesses/{id}/docs/)
    version           INT NOT NULL DEFAULT 1
    is_active         BOOLEAN DEFAULT true
    chunk_count       INT
    embedding_model   TEXT
    vector_index_path TEXT (deterministic: s3://bucket/businesses/{id}/index/)
    ingestion_job_id  UUID FK → ingestion_jobs.id
    uploaded_by       UUID FK → users.id

At any point in time, only one version of a document should have
is_active = true. When a new version is uploaded:

1.  The previous active version is set to is_active = false.
2.  A new record is created with version = previous_version + 1.
3.  The prior vector index for the Business is rebuilt and archived.

------------------------------------------------------------------------

### ingestion_jobs

    id                UUID PK
    document_ids      UUID[] FK → documents.id
    status            TEXT DEFAULT 'initiated'
                      (initiated | in_progress | success | failed)
    error_message     TEXT
    chunks_processed  INT DEFAULT 0
    started_at        TIMESTAMP
    completed_at      TIMESTAMP

------------------------------------------------------------------------

### usage_records

    id                UUID PK
    session_id        UUID FK → sessions.id
    message_id        UUID FK → messages.id
    stt_seconds       INT
    llm_tokens        INT
    tts_characters    INT
    cost_estimate     FLOAT

------------------------------------------------------------------------

### unknown_queries

    id                UUID PK
    session_id        UUID FK → sessions.id
    message_id        UUID FK → messages.id
    query_text        TEXT NOT NULL
    resolved          BOOLEAN DEFAULT false
    resolved_by       UUID FK → users.id

------------------------------------------------------------------------

### feedback

    id                UUID PK
    session_id        UUID FK → sessions.id
    message_id        UUID FK → messages.id
    rating            INT CHECK (rating >= 1 AND rating <= 5)
    comment           TEXT

------------------------------------------------------------------------

## Relationships

### Global → Tenant

businesses.schema_name maps to the tenant schema name (tenant\_\<slug\>).

### Within a Tenant Schema

    sessions         → messages          (one-to-many)
    sessions         → usage_records     (one-to-many)
    sessions         → unknown_queries   (one-to-many)
    sessions         → feedback          (one-to-many)
    documents        → ingestion_jobs    (one-to-many)

------------------------------------------------------------------------

## Key Indexes

    sessions:         (business_id, created_on), (user_identifier)
    messages:         (session_id, created_on)
    businesses:       (org_id), (slug)
    business_api_keys: (business_id), (api_key)
