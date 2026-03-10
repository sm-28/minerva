"""
core/pipelines/components/stt_component.py — Speech-to-Text component.

Purpose:
    Transcribes audio input into text. This is a CRITICAL component —
    pipeline aborts if it fails after retries and alternate provider.

Input (from context):
    context.audio_bytes     — raw audio data
    context.language_hint   — language code or 'auto'

Output (to context):
    context.transcript          — transcribed text
    context.detected_language   — detected language code (e.g. 'en-IN')

Provider:
    Uses ProviderResolver to get the active STTProvider
    (e.g. STT_Sarvam, STT_Deepgram).

should_execute:
    Returns True if context.audio_bytes is not None.
    Returns False for text-only input (context.text_input is used directly).
"""
