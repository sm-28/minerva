"""
core/services/session_service.py — Session management service.

Purpose:
    Encapsulates all session-related database operations and business logic.

Methods:
    create_session(client_id, channel, user_identifier, language) → Session
    get_session(session_id, tenant_schema) → Session
    update_session(session_id, updates) → Session
    end_session(session_id) → Session
    update_conversation_summary(session_id, summary)
    update_goal_state(session_id, goal_state_json)

Notes:
    - All methods operate within the tenant schema.
    - Session reads/writes happen at pipeline boundaries, not inside components.
"""
