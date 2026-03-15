"""
core/pipelines/pipeline_builder.py — Config-driven pipeline composition.

Purpose:
    Reads the client's pipeline_components configuration from ConfigCache
    and builds an ordered list of PipelineComponent instances using the
    ComponentRegistry.

Default Pipeline Order:
    STT → Translation → Memory → RAG → GoalSteering → LLM → TTS

Clients can customise their pipeline via the client_configs table
(config_key = 'pipeline_components') to disable specific components.

Usage:
    builder = PipelineBuilder(client_id="uuid")
    components = builder.build()
    runner = PipelineRunner(components)
    result = runner.run(context)

Notes:
    - Uses ConfigCache singleton to read client config (no DB query).
    - Uses ComponentRegistry to resolve component names to classes.
    - Components are instantiated fresh for each pipeline run.
"""
