"""
core/pipelines/registry/component_registry.py — Component Registry.

Purpose:
    Maps component name strings to their corresponding Python classes.
    PipelineBuilder uses this registry to resolve component names from
    client_configs into actual class instances.

Registry Map:
    "stt"            → STTComponent
    "translation"    → TranslationComponent
    "memory"         → ConversationMemoryComponent
    "rag"            → RAGComponent
    "goal_steering"  → GoalSteeringComponent
    "llm"            → LLMComponent
    "tts"            → TTSComponent

Usage:
    component_class = COMPONENT_REGISTRY["stt"]
    component = component_class()

Notes:
    - New components must be registered here to be available in pipelines.
    - The registry is a simple dict — no dynamic discovery.
"""
