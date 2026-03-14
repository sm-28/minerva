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

import logging
import os
import sys
import json
from datetime import datetime, timezone


class ContextFilter(logging.Filter):
    """Injects contextual fields (session_id, job_id) into log records."""

    def __init__(self, extra: dict | None = None):
        super().__init__()
        self.extra = extra or {}

    def filter(self, record: logging.LogRecord) -> bool:
        for key, value in self.extra.items():
            setattr(record, key, value)
        # Ensure defaults so formatters don't break
        if not hasattr(record, "session_id"):
            record.session_id = "-"
        if not hasattr(record, "job_id"):
            record.job_id = "-"
        return True


class JsonFormatter(logging.Formatter):
    """Structured JSON formatter for production / CloudWatch."""

    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "session_id": getattr(record, "session_id", "-"),
            "job_id": getattr(record, "job_id", "-"),
        }
        if record.exc_info:
            log_record["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(log_record)


def get_logger(name: str, extra: dict | None = None) -> logging.Logger:
    """
    Return a named logger configured for the current environment.

    Args:
        name:  Logger name (e.g. 'ingestion.pipeline.parser').
        extra: Optional dict of static context fields (e.g. job_id).

    Returns:
        A configured logging.Logger instance.
    """
    logger = logging.getLogger(name)

    # Avoid adding handlers multiple times (e.g. on re-import)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stdout)

    env = os.getenv("ENV", "local").lower()
    if env in ("production", "staging"):
        handler.setFormatter(JsonFormatter())
    else:
        fmt = (
            "%(asctime)s | %(levelname)-8s | %(name)s "
            "| job=%(job_id)s | %(message)s"
        )
        handler.setFormatter(logging.Formatter(fmt, datefmt="%Y-%m-%dT%H:%M:%S"))

    ctx_filter = ContextFilter(extra)
    handler.addFilter(ctx_filter)
    logger.addHandler(handler)
    logger.propagate = False

    return logger
