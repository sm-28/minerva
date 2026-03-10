"""
shared/models/feedback.py — User feedback model.

Table: tenant_<slug>.feedback

Fields:
    id, session_id (FK → sessions), message_id (FK → messages),
    rating (1-5), comment
"""
