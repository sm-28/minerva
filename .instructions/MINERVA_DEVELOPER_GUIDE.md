# MINERVA_DEVELOPER_GUIDE.md

## Purpose

Developer guide for contributing to Minerva.

Minerva uses a **pipeline component architecture**.

------------------------------------------------------------------------

# Services

core -- runtime conversation engine\
dashboard -- admin UI + backend API\
ingestion -- document processing

------------------------------------------------------------------------

# Pipeline Components

Example pipeline:

STT → Translation → Memory → RAG → Goal Steering → LLM → TTS

Each component modifies a shared **PipelineContext**.

------------------------------------------------------------------------

## Pipeline Directory

core/pipelines/

    pipeline_context.py
    pipeline_runner.py
    pipeline_builder.py
    components/
    registry/

------------------------------------------------------------------------

## PipelineContext

The shared data object passed through all components.

### Initial fields (set by core before pipeline starts)

    session_id           UUID
    client_id            UUID
    channel              str (web | whatsapp | phone)
    tenant_schema        str
    audio_bytes          bytes (raw input audio, if voice)
    text_input           str (raw text input, if text channel)
    language_hint        str (user-selected language or 'auto')
    config               dict (loaded from ConfigCache at pipeline start)

### Fields set by components during execution

    transcript           str                    — set by STTComponent
    detected_language    str                    — set by STTComponent
    translated_text      str                    — set by TranslationComponent
    conversation_summary str                    — set by MemoryComponent
    rag_chunks           list[dict]             — set by RAGComponent
    is_unknown           bool                   — set by RAGComponent
    goal_config          dict                   — set by GoalSteeringComponent
    goal_missing_fields  list                   — set by GoalSteeringComponent
    goal_steer_prompt    str                    — set by GoalSteeringComponent
    llm_response         str                    — set by LLMComponent
    audio_output         bytes                  — set by TTSComponent
    error                str                    — set if any component fails

Components read from and write to this context.
Do not store derived data in session state — use PipelineContext.

------------------------------------------------------------------------

## Component Base Class

All pipeline components inherit from PipelineComponent:

    class PipelineComponent:
        name: str

        def should_execute(self, context: PipelineContext) -> bool
        def execute(self, context: PipelineContext) -> PipelineContext

should_execute returns False to skip the component for this run.
execute must return the (modified) context.

If a component fails and is non-critical, it should catch the error,
log it, and return context unchanged.

If a component fails and is critical (STT, LLM), it should raise
PipelineAbortError to stop the pipeline.

------------------------------------------------------------------------

## PipelineRunner

Executes a list of components in sequence.

    runner = PipelineRunner(components=[...])
    result = runner.run(context)

The runner:

1.  Iterates through components in order.
2.  Calls should_execute(context) — skips if False.
3.  Calls execute(context) — updates context.
4.  On failure: retries 2x with exponential backoff.
5.  If retries exhausted: attempts alternate provider in that category.
6.  If alternate also fails: raises PipelineAbortError (critical) or
    logs and continues (non-critical).
7.  Returns the final PipelineContext.

All execution is synchronous within a single pipeline run.

------------------------------------------------------------------------

## PipelineBuilder

Reads client_configs to determine which components are active
and in what order.

    builder = PipelineBuilder(client_id)
    components = builder.build()

The default pipeline order is:

    STT → Translation → Memory → RAG → GoalSteering → LLM → TTS

Clients can disable components (e.g. no GoalSteering) via the
client_configs.pipeline_components config key.

------------------------------------------------------------------------

## Component Registry

Maps component names to classes.

registry/component_registry.py

    COMPONENT_REGISTRY = {
        "stt":            STTComponent,
        "translation":    TranslationComponent,
        "memory":         ConversationMemoryComponent,
        "rag":            RAGComponent,
        "goal_steering":  GoalSteeringComponent,
        "llm":            LLMComponent,
        "tts":            TTSComponent,
    }

PipelineBuilder uses this registry to resolve component names
from client_configs into actual class instances.

------------------------------------------------------------------------

## Example Component

    class GoalSteeringComponent(PipelineComponent):

        def should_execute(self, context):
            return context.goal_config is not None

        def execute(self, context):
            goal_config = GoalService.get_goal_config(context.client_id)
            missing = GoalService.get_missing_fields(goal_config, context.goal_state)
            context.goal_missing_fields = missing
            return context

------------------------------------------------------------------------

## Goal Steering

Ensures conversations move toward a client objective such as:

    collect_lead
    book_appointment
    support_request

### GoalService

    GoalService.get_goal_config(client_id) → dict
    GoalService.get_missing_fields(goal_config, goal_state) → list
    GoalService.update_goal_state(session_id, field, value)
    GoalService.is_complete(goal_config, goal_state) → bool

### Goal Types and Required Fields

    collect_lead:       name, email or phone, interest
    book_appointment:   preferred_date, preferred_time, contact
    support_request:    issue_description, severity

### Goal State

Goal state is stored in sessions.goal_state_json as JSONB.

### Goal Steering Intensity

Steering intensity increases with the turn count:

    Turns 1-2:   No steering (discovery phase)
    Turns 3-4:   Gentle nudge ("Would you like to schedule a visit?")
    Turns 5+:    Direct push ("Let's book a time — what works for you?")

A goal is marked complete when all required fields are collected
and the user confirms. The LLM appends [COMPLETE] to signal this.

------------------------------------------------------------------------

## Conversation Memory Component

MemoryComponent loads and updates the rolling conversation summary.

### execute(context) flow:

1.  Load conversation_summary from the session (via DB).
2.  If no summary exists and turn > 1: summarise the last 4 messages
    via LLM.
3.  If a summary exists and turn > 2: update the summary with the
    latest messages via LLM.
4.  Set context.conversation_summary.
5.  Persist the updated summary to sessions.conversation_summary.

This keeps the context window efficient for long conversations
by condensing history into a rolling summary rather than passing
all messages.

------------------------------------------------------------------------

## Rules

-   keep components small
-   use ProviderResolver for external providers
-   avoid raw SQL — use services for DB access
-   prompts must live in shared/prompts/
-   use singleton pattern for shared resources
-   all pipeline components must have unit tests
-   test should_execute and execute independently
-   use mock providers for external API calls in tests
