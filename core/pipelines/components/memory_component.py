"""
core/pipelines/components/memory_component.py — Conversation Memory component.

Purpose:
    Loads and updates the rolling conversation summary for context-efficient
    long conversations. This is a NON-CRITICAL component — on failure,
    the pipeline proceeds with an empty summary.

Input (from context):
    context.session_id  — to load existing summary from DB

Output (to context):
    context.conversation_summary — rolling summary string

Execution Flow:
    1. Load conversation_summary from the session record (DB read).
    2. If no summary and turn count > 1: summarise last 4 messages via LLM.
    3. If summary exists and turn count > 2: update summary with latest
       messages via LLM.
    4. Set context.conversation_summary.
    5. Persist updated summary to sessions.conversation_summary (DB write).

Notes:
    This component performs DB reads/writes, which is acceptable because
    it operates at the pipeline boundary (loading session context).
"""
