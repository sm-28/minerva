"""
core/services/usage_service.py — Usage tracking and cost estimation.

Purpose:
    Records per-message usage metrics for billing and analytics.

Methods:
    record_usage(session_id, message_id, stt_seconds, llm_tokens,
                 tts_characters, cost_estimate) → UsageRecord
    get_session_usage(session_id) → list[UsageRecord]
    get_total_cost(session_id) → float

Notes:
    - Usage records are written after each pipeline run.
    - Cost estimation formulas are configured via system_settings.
"""
