"""
core/pipelines/pipeline_context.py — Shared data object for pipeline execution.

Purpose:
    PipelineContext is the single data container that flows through every
    component in the pipeline. Components read inputs from it and write
    their outputs to it. This ensures a clean, traceable data flow
    without hidden state.

Initial Fields (set by core before pipeline starts):
    session_id           — UUID of the active session
    client_id            — UUID of the B2B client (tenant)
    channel              — str: 'web', 'whatsapp', or 'phone'
    tenant_schema        — str: database schema name (e.g. 'tenant_clientslug')
    audio_bytes          — bytes: raw input audio (if voice channel)
    text_input           — str: raw text input (if text channel)
    language_hint        — str: user-selected language or 'auto'
    config               — dict: client config loaded from ConfigCache

Fields Set by Components:
    transcript           — str (STTComponent)
    detected_language    — str (STTComponent)
    translated_text      — str (TranslationComponent)
    conversation_summary — str (MemoryComponent)
    rag_chunks           — list[dict] (RAGComponent)
    is_unknown           — bool (RAGComponent)
    goal_config          — dict (GoalSteeringComponent)
    goal_missing_fields  — list (GoalSteeringComponent)
    goal_steer_prompt    — str (GoalSteeringComponent)
    llm_response         — str (LLMComponent)
    audio_output         — bytes (TTSComponent)
    error                — str (set on component failure)

Usage:
    context = PipelineContext(session_id=..., client_id=..., ...)
    result = pipeline_runner.run(context)
    response_text = result.llm_response
    response_audio = result.audio_output
"""
