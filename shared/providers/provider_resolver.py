"""
shared/providers/provider_resolver.py — Dynamic provider selection (Singleton).

Purpose:
    Resolves which provider implementation to use for each category
    (STT, LLM, TTS, Translation) based on client configuration or
    system defaults.

Pattern:
    Singleton — one instance per process.

Methods:
    ProviderResolver.get_instance() → ProviderResolver
    resolver.get_provider(category: str, client_id: str) → Provider
    resolver.get_alternate_provider(category: str, current: str) → Provider

Resolution Order:
    1. client_configs.provider_overrides (per-tenant, highest priority)
    2. system_settings (global default, fallback)

Alternate Provider:
    Used by PipelineRunner when the primary provider fails after retries.
    Returns a different provider in the same category, if available.

Categories:
    'stt'          → STTProvider implementations
    'llm'          → LLMProvider implementations
    'tts'          → TTSProvider implementations
    'translation'  → TranslationProvider implementations
"""
