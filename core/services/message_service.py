"""
core/services/message_service.py — Message persistence service.

Purpose:
    Stores and retrieves conversation messages (user and assistant turns).

Methods:
    create_message(session_id, role, content, is_unknown, rag_context, audio_s3_path) → Message
    get_messages(session_id, limit) → list[Message]
    get_recent_messages(session_id, count) → list[Message]

Notes:
    - Messages are written after each pipeline run completes.
    - Audio files are stored in S3; only the S3 path is persisted here.
"""
