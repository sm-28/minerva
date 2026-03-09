# MINERVA_ARCHITECTURE.md

## 1. Overview

Minerva is a multi-tenant AI voice and chat platform that allows
businesses to deploy conversational AI assistants across channels such
as web widgets, WhatsApp, Telegram, and voice interfaces.

Core capabilities: - Speech to Text (STT) - Retrieval Augmented
Generation (RAG) - Large Language Model reasoning - Text to Speech
(TTS) - Multilingual interaction

Design goals: - Provider‑agnostic - Pipeline driven - Multi‑tenant -
Cost aware - Configurable

------------------------------------------------------------------------

## 2. Platform Components

Minerva consists of three deployable services:

1.  Dashboard
2.  Minerva API
3.  Ingestion Service

### Dashboard

Admin interface used by Client Admin and Super Admin.

Responsibilities: - document upload - channel integrations - analytics -
configuration management

### Minerva API

Core runtime that processes conversations.

Responsibilities: - request handling - pipeline execution - provider
orchestration - session tracking - usage tracking

### Ingestion Service

Responsible for converting documents into vector embeddings.

Responsibilities: - document parsing - chunking - embedding generation -
vector storage - ingestion status tracking

------------------------------------------------------------------------

## 3. Repository Structure

    minerva/
     ├── minerva-api/
     │   ├── api/
     │   ├── middleware/
     │   └── pipelines/
     │
     ├── minerva-ingestion/
     │   └── ingestion/
     │
     ├── shared/
     │   ├── interfaces/
     │   ├── providers/
     │   ├── services/
     │   ├── registry/
     │   ├── prompts/
     │   ├── models/
     │   └── utils/
     │
     └── infra/

------------------------------------------------------------------------

## 4. Runtime Flow

    Request
      ↓
    Middleware
      ↓
    API Handler
      ↓
    Pipeline Builder
      ↓
    Pipeline Runner
      ↓
    Pipeline Stages
      ↓
    Provider Resolver
      ↓
    Provider

------------------------------------------------------------------------

## 5. Pipeline Architecture

Minerva pipelines are composed of stages.

Example voice pipeline:

    STT → Translation → RAG → LLM → TTS

Each stage implements:

    execute(context)

Stages read and update a shared PipelineContext object.

------------------------------------------------------------------------

## 6. Provider Abstraction

Providers are accessed through a resolver.

    provider = ProviderResolver().get_provider("LLM", client_id)

Provider implementations live in:

    shared/providers/

Examples: - STT_Sarvam - STT_Deepgram - LLM_OpenAI - TTS_ElevenLabs

------------------------------------------------------------------------

## 7. Configuration Cache

Configuration is cached in memory to avoid database lookups.

Cache includes: - provider configuration - client overrides - pipeline
definitions - prompt overrides

Cache loads during application startup.

------------------------------------------------------------------------

## 8. Conversation Model

Each conversation has a session ID.

Database tables:

sessions messages

Prompt context includes:

-   system prompt
-   conversation summary
-   recent messages
-   RAG context
-   user query

------------------------------------------------------------------------

## 9. RAG Retrieval

RAG flow:

    User Query
       ↓
    Embedding
       ↓
    Vector Search
       ↓
    Top Chunks
       ↓
    Prompt Construction
       ↓
    LLM

Vector indexes are tenant isolated.

------------------------------------------------------------------------

## 10. Ingestion Pipeline

    Upload document
         ↓
    Text extraction
         ↓
    Chunking
         ↓
    Embedding generation
         ↓
    Vector storage

Existing index is backed up before re‑ingestion.

------------------------------------------------------------------------

## 11. Deployment

Typical deployment:

    Internet
       ↓
    Load Balancer
       ↓
    Minerva API (ECS Tasks)
       ↓
    PostgreSQL
    Vector DB
    S3

------------------------------------------------------------------------

## 12. Key Design Principles

-   provider abstraction
-   modular pipelines
-   multi‑tenant isolation
-   minimal runtime latency
-   configuration driven behavior
