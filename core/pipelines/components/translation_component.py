"""
core/pipelines/components/translation_component.py — Translation component.

Purpose:
    Translates the user's transcript to English for internal processing
    (RAG, LLM). Also translates the LLM response back to the user's
    language at the output stage. This is a NON-CRITICAL component —
    on failure, the pipeline proceeds with the original text.

Input (from context):
    context.transcript         — user's transcribed text
    context.detected_language  — source language code

Output (to context):
    context.translated_text    — English translation of the transcript

Provider:
    Uses ProviderResolver to get the active TranslationProvider.

should_execute:
    Returns True if detected_language is not 'en-IN'.
    Returns False if the transcript is already in English.
"""
