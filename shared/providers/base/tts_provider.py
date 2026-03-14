"""
shared/providers/base/tts_provider.py — TTS provider interface.

Purpose:
    Abstract base class that all Text-to-Speech providers must implement.

Interface:
    class TTSProvider(ABC):
        def text_to_speech(self, text: str, language_code: str,
                         speaker: str, pace: float) -> bytes
            Returns: WAV audio bytes

All TTS provider implementations must inherit from this class.
"""
