"""
shared/utils/logging.py — Structured logging setup.

Purpose:
    Configures structured logging with tenant and session context
    injected into every log record.

Features:
    - ContextFilter: injects user_id and session_id into log records
    - SessionFileHandler: routes logs to session-specific files
    - Structured JSON format for production (ECS CloudWatch)
    - Human-readable format for local development

Usage:
    from shared.utils.logging import get_logger
    logger = get_logger("component_name")
    logger.info("Processing message", extra={"session_id": "..."})
"""
