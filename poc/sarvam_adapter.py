"""
sarvam_adapter.py — Thin wrapper around the Sarvam AI Python SDK.

Auth: reads SARVAM_API_KEY from environment variables.
STT  : speech_to_text.transcribe()  — requires a WAV file-like object
Chat : chat.completions.create()     — synchronous
TTS  : text_to_speech.convert()      — returns base64 audio, decoded to bytes
"""

import io
import os
import base64
import logging
import time

from sarvamai import SarvamAI
from utils import get_logger

logger = get_logger("sarvam_adapter")

# ---------------------------------------------------------------------------
# Constants — easy to change without touching call sites
# ---------------------------------------------------------------------------

STT_MODEL    = "saaras:v3"          # Saaras v3 for high-performance STT
STT_MODE     = "transcribe"         # transcribe | translate | verbatim
CHAT_MODEL   = "sarvam-m"           # Sarvam multilingual LLM
TTS_MODEL    = "bulbul:v2"          # Reverted due to v3 API 500 errors
TTS_SPEAKER  = "anushka"            # Valid speaker for bulbul:v2
TTS_LANGUAGE = "en-IN"              # Language for TTS output
API_TIMEOUT  = 30                   # seconds for synchronous calls


# ---------------------------------------------------------------------------
# SarvamClient
# ---------------------------------------------------------------------------

class SarvamClient:
    """
    Wraps Sarvam AI SDK methods for the three pipeline stages:
        transcribe      — Speech-to-Text
        chat_completion — LLM response
        text_to_speech  — synthesise audio from text
        translate       — Text Translation
    """

    def __init__(self):
        api_key = os.environ.get("SARVAM_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "SARVAM_API_KEY environment variable is not set. "
                "Export it before running the app."
            )
        self._client = SarvamAI(api_subscription_key=api_key)

    # ------------------------------------------------------------------
    # 1. Speech-to-Text
    # ------------------------------------------------------------------

    def transcribe(self, audio_bytes: bytes, language_code: str = "en-IN", extension: str = "wav") -> tuple[str, str]:
        """
        Convert raw audio bytes (WAV format) to a transcript string.

        Args:
            audio_bytes: Raw WAV audio data.
            language_code: BCP-47 language code hint (default English India).

        Returns:
            Transcript string (may be empty if nothing was spoken).

        Raises:
            RuntimeError: If the API call fails after retries.
        """
        logger.debug("STT: sending %d bytes", len(audio_bytes))
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = f"audio.{extension}"  # SDK uses filename to infer format

        try:
            response = self._client.speech_to_text.transcribe(
                file=audio_file,
                model=STT_MODEL,
                mode=STT_MODE,
                language_code=language_code,
            )
            transcript = response.transcript if hasattr(response, "transcript") else str(response)
            detected_language_code = getattr(response, "language_code", None)
            if detected_language_code is None:
                detected_language_code = "unknown"
            else:
                detected_language_code = str(detected_language_code).strip()
            
            return transcript.strip(), detected_language_code
        except Exception as exc:
            logger.error("STT failed: %s", exc)
            raise RuntimeError(f"Speech-to-Text failed: {exc}") from exc

    # ------------------------------------------------------------------
    # 2. Chat Completion (RAG answer generation)
    # ------------------------------------------------------------------

    def chat_completion(self, system_prompt: str, user_prompt: str, temperature: float = 0.0, max_tokens: int = 500) -> str:
        """
        Generate a grounded answer using Sarvam LLM.

        Args:
            system_prompt: Instruction / persona for the model.
            user_prompt:   The user query (with injected context).
            temperature:   Sampling temperature (0 for deterministic).
            max_tokens:    limit the response length.

        Returns:
            The model's text response.
        """
        logger.debug("Chat: prompt length=%d chars", len(user_prompt))
        try:
            response = self._client.chat.completions(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            answer = response.choices[0].message.content
            return answer.strip()
        except Exception as exc:
            logger.error("Chat completion failed: %s", exc)
            raise RuntimeError(f"Chat completion failed: {exc}") from exc

    # ------------------------------------------------------------------
    # 3. Text-to-Speech
    # ------------------------------------------------------------------

    def text_to_speech(self, text: str, language_code: str = TTS_LANGUAGE, speaker: str = TTS_SPEAKER, pace: float = 0.9) -> bytes:
        """
        Convert text to audio bytes (WAV).

        Args:
            text:          The text to synthesise.
            language_code: BCP-47 language code for the voice.
            speaker:       The speaker voice name.
            pace:          The speed of the speech (0.5 to 2.0).

        Returns:
            WAV audio bytes ready for playback.

        Raises:
            RuntimeError: If the API call fails.
        """
        # Fallback for unknown language
        if str(language_code).strip().lower() == "unknown":
            logger.warning("TTS: received 'unknown' language code. Falling back to %s", TTS_LANGUAGE)
            language_code = TTS_LANGUAGE

        logger.debug("TTS: synthesising %d chars with speaker %s and pace %.2f", len(text), speaker, pace)
        try:
            response = self._client.text_to_speech.convert(
                text=text,
                target_language_code=language_code,
                pace=pace,
                speaker=speaker,
                model=TTS_MODEL,
            )
            # Join all audio portions (Sarvam may return multiple for long text)
            full_audio = bytearray()
            for i, b64 in enumerate(response.audios):
                chunk = base64.b64decode(b64)
                if i == 0:
                    full_audio.extend(chunk)
                else:
                    # Skip the 44-byte WAV header for subsequent chunks
                    full_audio.extend(chunk[44:])
            
            # Update the Master WAV header with the correct total size
            if len(full_audio) > 44:
                import struct
                # Offset 4 (file size - 8)
                full_audio[4:8] = struct.pack("<I", len(full_audio) - 8)
                # Offset 40 (data size)
                full_audio[40:44] = struct.pack("<I", len(full_audio) - 44)
            
            return bytes(full_audio)
        except Exception as exc:
            logger.error("TTS failed: %s", exc)
            raise RuntimeError(f"Text-to-Speech failed: {exc}") from exc

    # ------------------------------------------------------------------
    # 4. Translate
    # ------------------------------------------------------------------
    def translate(self, text: str, source_language: str, target_language: str) -> str:
        """
        Translate text from source language to target language.

        Args:
            text:          The text to translate.
            source_language: Source language code (BCP-47).
            target_language: Target language code (BCP-47).

        Returns:
            Translated text.

        Raises:
            RuntimeError: If the API call fails.
        """
        logger.debug("Translate: %s -> %s", source_language, target_language)
        try:
            response = self._client.text.translate(
                input=text,
                source_language_code=source_language,
                target_language_code=target_language,
                mode="formal",
                model="mayura:v1",
                numerals_format="native"
            )
            # The SDK returns TranslationResponse with 'translated_text' or similar
            # Based on user's code, we check for 'translated_text'
            translated_text = response.translated_text if hasattr(response, "translated_text") else str(response)
            return translated_text.strip()
        except Exception as exc:
            logger.error("Translate failed: %s", exc)
            raise RuntimeError(f"Translate failed: {exc}") from exc