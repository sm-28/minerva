"""
core/api/sessions.py — Session and message endpoints.

Purpose:
    Handles all conversation-related operations. Every request is
    authenticated via JWT middleware, which injects tenant context.

Endpoints:
    POST   /api/v1/sessions/{id}/message  — Send a text or audio message.
           Triggers the full pipeline (STT → ... → TTS) and returns
           the assistant's response with optional audio.

    GET    /api/v1/sessions/{id}          — Retrieve current session state
           including status, conversation summary, goal state, and
           turn count.

    DELETE /api/v1/sessions/{id}          — End the session. Sets status
           to 'ended', generates a final summary, and returns unknown
           questions list.

    WS     /api/v1/sessions/{id}/stream   — WebSocket endpoint for
           real-time bidirectional audio streaming. Used by voice
           channels for low-latency conversation.

Notes:
    - All endpoints extract client_id and session_id from the JWT.
    - The ALB sticky session ensures requests route to the same ECS task
      where the conversation memory is held in-process.
"""
