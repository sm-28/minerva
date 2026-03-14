"""
core/pipelines/pipeline_runner.py — Sequential pipeline executor.

Purpose:
    Receives an ordered list of PipelineComponent instances and a
    PipelineContext, then executes each component in sequence.

Execution Flow:
    1. Iterate through components in order.
    2. Call component.should_execute(context) — skip if False.
    3. Call component.execute(context) — updates context in place.
    4. On failure: retry up to 2 times with exponential backoff (1s, 2s).
    5. If retries exhausted: attempt with alternate provider via ProviderResolver.
    6. If alternate also fails:
       - Critical component (STT, LLM): raise PipelineAbortError.
       - Non-critical component: log error, continue with context unchanged.
    7. Return the final PipelineContext.

Usage:
    runner = PipelineRunner(components=[stt, translation, memory, ...])
    result = runner.run(context)

Notes:
    - All execution is synchronous within a single pipeline run.
    - The runner does not create or manage components — it receives them
      from PipelineBuilder.
"""
