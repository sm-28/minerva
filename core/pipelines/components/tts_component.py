"""
core/pipelines/components/tts_component.py — Text-to-Speech component.

Purpose:
    Converts the LLM's text response into audio for playback.
    This is a NON-CRITICAL component — on failure, the text response
    is returned without audio.

Input (from context):
    context.llm_response       — text to synthesise
    context.detected_language   — target language for speech

Output (to context):
    context.audio_output  — WAV audio bytes ready for playback

Provider:
    Uses ProviderResolver to get the active TTSProvider
    (e.g. TTS_ElevenLabs, TTS_Sarvam).

Notes:
    - If the response needs translation back to the user's language,
      that should happen before TTS (handled by a post-LLM translation step).
    - Voice and pace settings are read from client_configs via ConfigCache.
"""
