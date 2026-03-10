"""
core/services/goal_service.py — Goal steering business logic.

Purpose:
    Manages conversation goal state — loading goal configs, tracking
    collected fields, and determining goal completion.

Methods:
    get_goal_config(client_id) → dict
    get_missing_fields(goal_config, goal_state) → list
    update_goal_state(session_id, field, value)
    is_complete(goal_config, goal_state) → bool

Goal Types:
    collect_lead       — requires: name, email/phone, interest
    book_appointment   — requires: preferred_date, preferred_time, contact
    support_request    — requires: issue_description, severity

Notes:
    - Goal config is read from ConfigCache (no DB query).
    - Goal state is stored in sessions.goal_state_json.
"""
