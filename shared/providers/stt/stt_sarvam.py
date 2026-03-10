"""
shared/providers/stt/stt_sarvam.py — Sarvam AI STT provider.

Purpose:
    Implements STTProvider using the Sarvam AI Speech-to-Text API.

Provider Name: 'stt_sarvam'

API Details:
    Model: saaras:v3
    Supports: multiple Indian languages + auto-detect
    Auth: SARVAM_API_KEY environment variable

Notes:
    - Requires WAV audio input.
    - Returns transcript and detected language code.
    - Timeout: 30 seconds.
"""
