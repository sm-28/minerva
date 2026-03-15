"""
shared/providers/base/stt_provider.py — STT provider interface.

Purpose:
    Abstract base class that all Speech-to-Text providers must implement.

Interface:
    class STTProvider(ABC):
        def transcribe(self, audio_bytes: bytes, language_code: str) -> tuple[str, str]
            Returns: (transcript, detected_language_code)

All STT provider implementations (Sarvam, Deepgram, etc.) must
inherit from this class and implement the transcribe method.
"""
