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
