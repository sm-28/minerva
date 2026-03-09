# COPILOT_INSTRUCTIONS.md

## Purpose

This document provides instructions for AI coding assistants (GitHub
Copilot, Cursor, etc.) working on the Minerva codebase.

Minerva is a **multi-tenant AI conversational platform** with modular
pipelines, provider abstraction, and strict architectural boundaries.

AI-generated code must follow the architecture described here.

------------------------------------------------------------------------

# 1. High Level Architecture

Minerva consists of three primary services:

    Dashboard
    Minerva API
    Ingestion Service

Responsibilities:

  Service             Responsibility
  ------------------- ------------------------------------------------
  Dashboard           Admin UI, document uploads, configuration
  Minerva API         Conversation processing and pipeline execution
  Ingestion Service   Document parsing, chunking and embedding

------------------------------------------------------------------------

# 2. Runtime Flow

All requests must follow this architecture:

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
    Providers

Code must not bypass this flow.

------------------------------------------------------------------------

# 3. Repository Structure

    minerva/

    minerva-api/
        api/
        middleware/
        pipelines/

    minerva-ingestion/
        ingestion/

    shared/
        interfaces/
        providers/
        services/
        registry/
        prompts/
        models/
        utils/

    infra/

AI assistants must generate code in the correct folder.

------------------------------------------------------------------------

# 4. API Layer Rules

API endpoints live in:

    minerva-api/api/

Responsibilities:

-   validate requests
-   attach session context
-   trigger pipeline execution

API layer must **not contain business logic**.

Example:

``` python
pipeline = PipelineBuilder().build("chat")
response = pipeline.run(context)
```

------------------------------------------------------------------------

# 5. Middleware

Middleware lives in:

    minerva-api/middleware/

Middleware handles:

-   authentication
-   trial validation
-   tenant resolution
-   request logging

Pipelines must not implement these checks.

------------------------------------------------------------------------

# 6. Pipeline Architecture

Pipelines orchestrate AI workflows.

Location:

    minerva-api/pipelines/

Stages live in:

    pipelines/stages/

All stages must implement:

    execute(context)

Stages must:

-   read from context
-   update context
-   return context

------------------------------------------------------------------------

# 7. Pipeline Context

PipelineContext carries state across stages.

Typical fields:

    client_id
    session_id
    channel
    audio_input
    text_input
    retrieved_context
    llm_response
    audio_output
    usage

Stages should update context rather than passing multiple parameters.

------------------------------------------------------------------------

# 8. Pipeline Registry

Pipelines must be defined via configuration.

Location:

    shared/registry/pipeline_registry.py

Example:

``` python
PIPELINE_REGISTRY = {
    "voice": ["stt", "rag", "llm", "tts"],
    "chat": ["rag", "llm"]
}
```

Do not hardcode pipelines inside API handlers.

------------------------------------------------------------------------

# 9. Provider Abstraction

Providers must be accessed via resolver.

Correct:

``` python
provider = ProviderResolver().get_provider("LLM", client_id)
```

Incorrect:

``` python
OpenAIClient()
```

Provider implementations live in:

    shared/providers/

Examples:

-   STT_Sarvam
-   STT_Deepgram
-   LLM_OpenAI
-   TTS_ElevenLabs

------------------------------------------------------------------------

# 10. Provider Interfaces

All providers must implement base interfaces.

Location:

    shared/interfaces/

Examples:

    BaseSTT
    BaseLLM
    BaseTTS
    BaseEmbedding

------------------------------------------------------------------------

# 11. Provider Options Pattern

Providers receive a generic options dictionary.

Example:

``` python
options = {
  "voice": "female",
  "speed": 1.0
}
```

Providers translate generic options into provider-specific parameters
internally.

------------------------------------------------------------------------

# 12. Configuration Access

Configuration must come from **in-memory config cache**.

Correct:

``` python
config = ConfigCache.get_client_config(client_id)
```

Avoid database calls during request execution.

------------------------------------------------------------------------

# 13. Prompt Management

Prompts live in:

    shared/prompts/

Prompts must not be embedded inside pipeline or provider code.

Prompt assembly should occur in a dedicated service.

------------------------------------------------------------------------

# 14. Database Access Rules

Database operations must occur through services.

Examples:

    session_service
    conversation_service
    usage_service
    config_service

Avoid direct SQL inside pipeline stages.

------------------------------------------------------------------------

# 15. Cost Tracking

Provider usage must be recorded **once per request**.

Metrics tracked:

-   STT seconds
-   LLM tokens
-   TTS characters

------------------------------------------------------------------------

# 16. Tenant Isolation

Minerva uses tenant-specific schemas.

All operations must be scoped to the tenant schema derived from:

    clients.schema_name

Never mix data between tenants.

------------------------------------------------------------------------

# 17. Logging Guidelines

Logs should include:

    timestamp
    client_id
    session_id
    component
    event

Sensitive data must never be logged.

------------------------------------------------------------------------

# 18. Ingestion Pipeline

Location:

    minerva-ingestion/ingestion/

Flow:

    Upload document
       ↓
    Extract text
       ↓
    Chunk content
       ↓
    Generate embeddings
       ↓
    Store vectors

Each ingestion job must update ingestion status in the database.

------------------------------------------------------------------------

# 19. Adding New Providers

Steps:

1.  Implement provider class
2.  Extend base interface
3.  Register provider in provider registry

Example location:

    shared/providers/llm/LLM_Gemini.py

------------------------------------------------------------------------

# 20. Adding New Pipeline Stages

Steps:

1.  Create stage class
2.  Implement execute(context)
3.  Register stage
4.  Add stage to pipeline registry

------------------------------------------------------------------------

# 21. Coding Principles

All generated code should follow:

-   modular design
-   provider abstraction
-   configuration-driven behavior
-   strict tenant isolation
-   minimal database calls during requests

------------------------------------------------------------------------

# Summary

Minerva is an **AI platform architecture**, not a simple chatbot.

AI-generated code must:

-   respect architectural boundaries
-   use pipeline stages
-   use provider resolver
-   avoid direct provider calls
-   avoid direct database access in pipelines
