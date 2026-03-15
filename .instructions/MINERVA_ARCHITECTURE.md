# MINERVA_ARCHITECTURE.md

## Overview

Minerva is a modular AI conversation platform built around a **pipeline
component architecture** and a **multi‑tenant data model**.

The platform consists of three primary services:

-   **core** -- handles user conversations (chat / voice / sessions /
    pipelines)
-   **dashboard** -- admin UI + admin API
-   **ingestion** -- document ingestion pipeline

Shared logic lives in **shared/**.

------------------------------------------------------------------------

## Repository Structure

minerva/
├── core/
├── dashboard/
├── ingestion/
├── shared/
├── infra/
├── docs/
├── MINERVA_ARCHITECTURE.md
├── MINERVA_DEVELOPER_GUIDE.md
├── MINERVA_DATA_MODEL.md
└── COPILOT_INSTRUCTIONS.md

------------------------------------------------------------------------

## Pipeline Flow

STT → Translation → Conversation Memory → RAG → Goal Steering → LLM →
TTS

Each step is implemented as a **component**.

Components implement:

should_execute(context)\
execute(context)

------------------------------------------------------------------------

## Core API

core exposes a FastAPI-based REST + WebSocket API.

Key endpoints:

    POST   /api/v1/auth/token                  — generate session token
    POST   /api/v1/sessions/{id}/message        — send a message (text or audio)
    GET    /api/v1/sessions/{id}                — retrieve session state
    DELETE /api/v1/sessions/{id}                — end session
    WS     /api/v1/sessions/{id}/stream         — real-time bidirectional audio
    POST   /internal/cache/refresh              — force config reload (internal only)

All endpoints (except /auth/token) require a valid JWT token.

------------------------------------------------------------------------

## Authentication & Security

Minerva uses a hierarchical B2B token-based authentication model.

### Organization & Business Onboarding (via Dashboard)

1.  Admin creates an Organization record (the billing entity).
2.  Admin creates one or more Business records under the Organization.
3.  System generates an api_key + api_secret pair scoped to a specific Business.
4.  Organization admin configures allowed_domains and allowed_ips for each business.
5.  Credentials (keys) are provided to the development team.
6.  A business can have a maximum of 2 active api_key pairs at any time
    to support key rotation without downtime.

### Runtime Auth Flow

    Customer Browser         Client's Backend         Minerva Core
         │                         │                       │
         │  1. "Start chat"        │                       │
         │────────────────────────>│                       │
         │                         │                       │
         │                         │  2. POST /api/v1/auth/token
         │                         │     { api_key, api_secret,
         │                         │       customer_identifier }
         │                         │──────────────────────>│
         │                         │                       │
         │                         │  3. Validate:         │
         │                         │     - api_key exists  │
         │                         │     - api_secret matches
         │                         │     - origin IP in    │
         │                         │       allowed_ips     │
         │                         │     - origin domain in│
         │                         │       allowed_domains │
         │                         │     - Create session  │
         │                         │     - Generate JWT    │
         │                         │       (30-min TTL)    │
         │                         │                       │
         │                         │  4. { token: "eyJ..." }
         │                         │<──────────────────────│
         │                         │                       │
         │  5. Set-Cookie:         │                       │
         │     minerva_token=...   │                       │
         │<────────────────────────│                       │
         │                         │                       │
         │  6. All subsequent requests go DIRECTLY to      │
         │     Minerva Core with cookie/token              │
         │────────────────────────────────────────────────>│
         │                         │                       │
         │                         │  7. Middleware:        │
         │                         │     - Validate JWT    │
         │                         │     - Extract org_id, business_id
         │                         │     - Extract session │
         │                         │     - Route via ALB   │
         │                         │       sticky session  │
         │                         │                       │

### JWT Token Contents

    {
      "sub": "customer_identifier",
      "org_id": "uuid-of-organization",
      "business_id": "uuid-of-business",
      "session_id": "uuid-of-session",
      "schema": "tenant_business_slug",
      "exp": <30-min-from-now>,
      "iat": <issued-at>
    }

### Token Refresh

Sliding window: if the customer is still active at the 25-minute mark,
the middleware auto-extends by issuing a new token. If the token expires
(customer went idle for 30+ minutes), a new token must be obtained via
the client's backend.

### Security Layers

-   api_key + api_secret never touch the customer's browser — only the
    client's backend uses them.
-   Domain whitelisting validates the Origin header at token generation.
-   IP whitelisting validates the source IP at token generation.
-   JWT is the only credential in the customer's browser (cookie).
-   ALB sticky session uses the token/cookie for routing.

------------------------------------------------------------------------

## Channel Architecture

External channels connect to core via channel adapters.

    Web UI      → REST/WebSocket  → core
    WhatsApp    → Webhook Receiver → core REST API
    Phone/IVR   → Telephony Gateway → core WebSocket

Each adapter normalises input into a standard PipelineContext
and writes the channel type to sessions.channel.

After the initial token exchange, the customer's browser communicates
directly with Minerva Core for lowest latency (especially critical
for real-time voice via WebSocket).

------------------------------------------------------------------------

## Dashboard

Contains both:

frontend (UI)\
backend (admin API)

Responsibilities:

-   document uploads
-   business configuration
-   analytics (aggregated by org or per business)
-   logs
-   ingestion triggers
-   API key management (scoped to business)
-   domain and IP whitelisting management

Dashboard does not communicate directly with core.
Settings updated via dashboard are written to the database.
Core loads settings into memory at startup and refreshes
periodically (every 5 minutes).

------------------------------------------------------------------------

## Ingestion

Processes documents into vector knowledge.

Upload → Parse → Chunk → Embed → Store

### Ingestion Trigger Flow

1.  User uploads a document via Dashboard.
2.  Dashboard creates an entry in the documents table and an
    ingestion_jobs record with status = 'initiated'.
3.  Dashboard triggers an ECS ingestion task, passing the
    ingestion job ID.
4.  The ingestion ECS task reads all required info from the database,
    processes the document, and updates the ingestion_jobs status
    through: initiated → in_progress → success | failed.
5.  Dashboard UI polls the ingestion API every 5 seconds to get
    the current job status and reflects it in the UI.

### Vector Index Strategy

-   One vector index exists per Business (not per Org).
-   When a new document version is ingested, the Business's vector
    index is rebuilt with all active documents for that business.
-   Prior vector index versions are archived in S3 under a folder
    named with the ingestion job ID.
-   Old document files are retained in S3 for audit purposes.

------------------------------------------------------------------------

## Inter-Service Communication

Dashboard and core do not communicate with each other directly.
Configuration is shared via the database:

    dashboard:  writes business_configs, system_settings to DB
    core:       reads configs from DB (keyed by business_id)
                refreshed every 5 minutes

    dashboard → ingestion:  Direct ECS task trigger with job ID
    ingestion → DB:         Reads job details, writes status updates

Service data ownership:

    core:       owns sessions, messages, usage_records
    dashboard:  owns organizations, businesses, business_configs, system_settings, business_api_keys
    ingestion:  owns documents, ingestion_jobs
    billing:    aggregates usage across businesses under an organization

------------------------------------------------------------------------

## Pipeline Error Strategy

    If STT fails:           retry 2x → try alternate STT provider → abort pipeline, return error
    If Translation fails:   retry 2x → try alternate provider → skip, proceed with original text
    If Memory fails:        retry 2x → try alternate provider → skip, proceed with empty summary
    If RAG fails:           retry 2x → try alternate provider → proceed with empty context
    If Goal Steering fails: retry 2x → try alternate provider → skip, no goal nudge this turn
    If LLM fails:           retry 2x → try alternate LLM provider → abort pipeline, return error
    If TTS fails:           retry 2x → try alternate TTS provider → return text response only

Retry strategy: exponential backoff (1s, 2s).
After retries exhausted: attempt the same operation with an alternate
provider in that category (e.g. if STT_Sarvam fails, try STT_Deepgram).
If the alternate provider also fails, take the default action listed above.

core must never crash on a single component failure.

------------------------------------------------------------------------

## Deployment Architecture

### AWS Infrastructure

    Dashboard:   EC2 instance
    Core:        ECS (Fargate or EC2-backed)
                   - Minimum desired tasks: 2
                   - Maximum tasks: 5
                   - ALB with sticky sessions (cookie-based)
                   - Sticky sessions required because conversation
                     memory is held in-process on the ECS task
    Ingestion:   ECS (Fargate or EC2-backed)
                   - Minimum desired tasks: 0
                   - Maximum tasks: 2
                   - Triggered on-demand by dashboard
    Database:    RDS PostgreSQL 15+
    Storage:     S3 (documents, audio, archived vector indexes)

### Why Sticky Sessions on Core

Core holds the active conversation context (PipelineContext,
conversation summary, goal state) in memory on the ECS task for
the duration of a session. The ALB sticky session ensures all
requests from a customer route to the same task using the JWT
cookie. If a task goes down, the session is lost and the customer
must re-authenticate to start a new session.

------------------------------------------------------------------------

## Design Principles

-   modular components
-   provider abstraction
-   tenant isolation
-   configurable client goals
-   singleton pattern for shared resources (ConfigCache, ProviderResolver)
-   no Redis — in-memory caching with periodic DB refresh
