"""
shared/models/session.py — Conversation session model.

Table: tenant_<slug>.sessions

Fields:
    id, client_id, channel, user_identifier, language, status,
    conversation_summary, audio_s3_path, goal_state_json,
    last_activity, ended_at
"""
