# COPILOT_INSTRUCTIONS.md

Guidelines for AI coding assistants working on the Minerva repository.

------------------------------------------------------------------------

# Services

core\
dashboard\
ingestion

Shared code lives in:

shared/

------------------------------------------------------------------------

# Pipeline Architecture

core executes pipelines made of **components**.

Components must implement:

should_execute(context)\
execute(context)

------------------------------------------------------------------------

# Providers

Providers exist in:

shared/providers/

Examples:

STT_Sarvam\
STT_Deepgram\
LLM_OpenAI\
TTS_ElevenLabs

Access via:

ProviderResolver.get_provider(category, provider_name)

## Provider Interfaces

Every provider must implement its category interface:

    STTProvider:
        transcribe(audio_bytes, language_code) → (transcript, detected_language)

    LLMProvider:
        chat_completion(system_prompt, user_prompt, temperature, max_tokens) → str

    TTSProvider:
        text_to_speech(text, language_code, speaker, pace) → bytes

    TranslationProvider:
        translate(text, source_lang, target_lang) → str

ProviderResolver reads the active provider for each category from:

1.  client_configs.provider_overrides (per-tenant, highest priority)
2.  system_settings (global default, fallback)

When a provider fails after retries, ProviderResolver automatically
attempts the alternate provider in that category before giving up.

------------------------------------------------------------------------

# Configuration

Use ConfigCache for runtime configuration.

## ConfigCache

ConfigCache is an in-memory singleton loaded from the database
at service startup.

    ConfigCache.get_client_config(client_id) → dict
    ConfigCache.get_system_setting(key) → value
    ConfigCache.invalidate(client_id)

Backend: in-memory dictionary.
Refresh: a background thread reloads from the database every 5 minutes.
No Redis — all caching is in-process.

For immediate refresh (e.g. after a critical config change), dashboard
can optionally call core's internal endpoint:

    POST /internal/cache/refresh

This endpoint is not publicly accessible (internal network only).

## DB Access Rules

Avoid DB queries in the hot path (inside pipeline component execution).
Pre-load client config and session data before the pipeline starts.
Session reads/writes at pipeline boundaries (start and end) are acceptable.

------------------------------------------------------------------------

# Singleton Pattern

Use the singleton pattern wherever applicable to avoid multiple
copies of the same object across sessions and clients.

Apply to:

-   ConfigCache — one instance per process, shared across all sessions
-   ProviderResolver — one instance, reused for provider lookups
-   Database connection pool — one pool per process
-   Embedding model — loaded once, shared across requests

Do not create new instances of these in request handlers or components.

------------------------------------------------------------------------

# Prompts

Prompts must live in:

shared/prompts/

Never hardcode prompts in components.

------------------------------------------------------------------------

# Error Handling

Components must never raise unhandled exceptions.

Critical components (STT, LLM):
    Raise PipelineAbortError on failure after retries + alternate provider.

Non-critical components (Translation, Memory, GoalSteering, TTS):
    Catch errors, log them, and return context unchanged.

All provider calls must have timeout handling.

Retry strategy:
    1.  Retry the failed call up to 2 times with exponential backoff.
    2.  If retries exhausted, attempt the same call with an alternate
        provider in that category.
    3.  If the alternate provider also fails, take the default action
        (abort for critical, skip for non-critical).

------------------------------------------------------------------------

# Testing

All pipeline components must have unit tests.
Test should_execute and execute independently.
Use mock providers for external API calls.
Integration tests should cover full pipeline with test fixtures.

------------------------------------------------------------------------

# Coding Rules

-   isolate providers behind interfaces
-   maintain tenant isolation (schema-per-tenant)
-   keep components small and focused
-   avoid unnecessary DB calls — use ConfigCache
-   use singleton pattern for shared resources
-   never store secrets in code — use environment variables
-   all tables must include audit columns (created_by, created_on,
    last_updated_by, last_updated_on)
