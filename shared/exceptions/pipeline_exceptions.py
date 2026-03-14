"""
shared/exceptions/pipeline_exceptions.py — Pipeline-specific exceptions.

Purpose:
    Defines custom exceptions used by pipeline components and the
    PipelineRunner to control execution flow.

Exceptions:
    PipelineAbortError:
        Raised by critical components (STT, LLM) when they fail after
        all retries and alternate provider attempts are exhausted.
        PipelineRunner catches this and stops the pipeline, returning
        an error response to the caller.

    ProviderError:
        Raised by provider implementations when an external API call fails.
        Contains provider name, category, and the underlying error.
        PipelineRunner uses this to trigger the alternate provider logic.
"""


class PipelineAbortError(Exception):
    """
    Raised when a critical pipeline stage cannot be recovered.

    Attributes:
        stage:   Name of the pipeline stage that failed (e.g. 'stt', 'llm').
        message: Human-readable description of the failure.
    """

    def __init__(self, stage: str, message: str) -> None:
        super().__init__(f"[{stage}] {message}")
        self.stage = stage
        self.message = message


class ProviderError(Exception):
    """
    Raised by a provider implementation when an external API call fails.

    Attributes:
        provider:  Provider name (e.g. 'sarvam', 'deepgram').
        category:  Pipeline category (e.g. 'stt', 'tts', 'llm').
        cause:     The underlying exception, if any.
    """

    def __init__(self, provider: str, category: str, cause: Exception | None = None) -> None:
        msg = f"Provider '{provider}' in category '{category}' failed"
        if cause:
            msg += f": {cause}"
        super().__init__(msg)
        self.provider = provider
        self.category = category
        self.cause = cause


class IngestionError(Exception):
    """
    Raised when the ingestion pipeline encounters an unrecoverable error.

    Attributes:
        stage:   Name of the ingestion stage (e.g. 'parse', 'chunk', 'embed').
        message: Human-readable description of the failure.
    """

    def __init__(self, stage: str, message: str) -> None:
        super().__init__(f"[ingestion:{stage}] {message}")
        self.stage = stage
        self.message = message
