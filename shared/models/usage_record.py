"""
shared/models/usage_record.py — Per-message usage tracking model.

Table: tenant_<slug>.usage_records

Fields:
    id, session_id (FK → sessions), message_id (FK → messages),
    stt_seconds, llm_tokens, tts_characters, cost_estimate
"""
