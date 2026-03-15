"""
shared/models/message.py — Conversation message model.

Table: tenant_<slug>.messages

Fields:
    id, session_id (FK → sessions), role, content,
    audio_s3_path, is_unknown, rag_context (JSONB)
"""
