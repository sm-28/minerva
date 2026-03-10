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

ProviderResolver.get_provider()

------------------------------------------------------------------------

# Configuration

Use ConfigCache for runtime configuration.

Avoid DB queries in request path.

------------------------------------------------------------------------

# Prompts

Prompts must live in:

shared/prompts/

Never hardcode prompts in components.

------------------------------------------------------------------------

# Coding Rules

-   isolate providers
-   maintain tenant isolation
-   keep components small
-   avoid unnecessary DB calls
