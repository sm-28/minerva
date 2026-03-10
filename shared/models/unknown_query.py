"""
shared/models/unknown_query.py — Unknown query tracking model.

Table: tenant_<slug>.unknown_queries

Fields:
    id, session_id (FK → sessions), message_id (FK → messages),
    query_text, resolved, resolved_by (FK → users)
"""
