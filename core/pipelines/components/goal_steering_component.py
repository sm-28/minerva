"""
core/pipelines/components/goal_steering_component.py — Goal Steering component.

Purpose:
    Evaluates conversation progress toward the client's business objective
    and injects steering prompts into the LLM context. This is a
    NON-CRITICAL component — on failure, no goal steering occurs.

Input (from context):
    context.client_id       — to load goal configuration
    context.session_id      — to load current goal state

Output (to context):
    context.goal_config         — goal type and required fields
    context.goal_missing_fields — list of fields still needed
    context.goal_steer_prompt   — steering instruction for the LLM

Goal Types:
    collect_lead       — requires: name, email/phone, interest
    book_appointment   — requires: preferred_date, preferred_time, contact
    support_request    — requires: issue_description, severity

Steering Intensity (turn-based):
    Turns 1-2:  No steering (discovery phase)
    Turns 3-4:  Gentle nudge
    Turns 5+:   Direct push

Completion:
    When all required fields are collected and user confirms,
    the LLM appends [COMPLETE] to signal goal achievement.

Uses GoalService for all goal state operations.
"""
