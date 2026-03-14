"""
tests/shared/test_exceptions.py — Tests for custom exception classes.

Covers:
    - PipelineAbortError carries stage and message attributes
    - ProviderError carries provider, category, and cause
    - IngestionError carries stage and message attributes
    - Exception messages are correctly formatted
    - All exceptions are subclasses of Exception
"""

from __future__ import annotations

import pytest

from shared.exceptions.pipeline_exceptions import (
    IngestionError,
    PipelineAbortError,
    ProviderError,
)


class TestPipelineAbortError:
    def test_is_exception(self):
        assert issubclass(PipelineAbortError, Exception)

    def test_attributes(self):
        err = PipelineAbortError("stt", "Speech recognition failed")
        assert err.stage == "stt"
        assert err.message == "Speech recognition failed"

    def test_str_contains_stage_and_message(self):
        err = PipelineAbortError("llm", "Token limit exceeded")
        assert "llm" in str(err)
        assert "Token limit exceeded" in str(err)

    def test_can_be_raised_and_caught(self):
        with pytest.raises(PipelineAbortError) as exc_info:
            raise PipelineAbortError("tts", "No audio output")
        assert exc_info.value.stage == "tts"


class TestProviderError:
    def test_is_exception(self):
        assert issubclass(ProviderError, Exception)

    def test_attributes_without_cause(self):
        err = ProviderError("sarvam", "stt")
        assert err.provider == "sarvam"
        assert err.category == "stt"
        assert err.cause is None

    def test_attributes_with_cause(self):
        cause = ConnectionError("timeout")
        err = ProviderError("deepgram", "stt", cause=cause)
        assert err.cause is cause

    def test_str_includes_provider_and_category(self):
        err = ProviderError("openai", "llm")
        msg = str(err)
        assert "openai" in msg
        assert "llm" in msg

    def test_str_includes_cause_when_provided(self):
        err = ProviderError("openai", "llm", cause=RuntimeError("API error"))
        assert "API error" in str(err)

    def test_can_be_raised_and_caught(self):
        with pytest.raises(ProviderError):
            raise ProviderError("google", "translation")


class TestIngestionError:
    def test_is_exception(self):
        assert issubclass(IngestionError, Exception)

    def test_attributes(self):
        err = IngestionError("parse", "Unsupported file type")
        assert err.stage == "parse"
        assert err.message == "Unsupported file type"

    def test_str_contains_stage_and_message(self):
        err = IngestionError("embed", "Model load failed")
        assert "embed" in str(err)
        assert "Model load failed" in str(err)

    def test_str_prefixed_with_ingestion(self):
        err = IngestionError("chunk", "Empty text")
        assert "ingestion" in str(err).lower()

    def test_can_be_raised_and_caught(self):
        with pytest.raises(IngestionError) as exc_info:
            raise IngestionError("vector_store", "FAISS write failed")
        assert exc_info.value.stage == "vector_store"

    def test_inherits_from_exception(self):
        err = IngestionError("download", "S3 error")
        assert isinstance(err, Exception)
