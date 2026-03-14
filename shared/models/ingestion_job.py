"""
shared/models/ingestion_job.py — Ingestion job model.

Table: tenant_<slug>.ingestion_jobs

Fields:
    id, document_id (FK → documents),
    status ('initiated' | 'in_progress' | 'success' | 'failed'),
    error_message, chunks_processed, started_at, completed_at
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


class IngestionStatus:
    INITIATED = "initiated"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class IngestionJob:
    """
    Represents a row in tenant_<slug>.ingestion_jobs.

    Status lifecycle: initiated → in_progress → success | failed
    """

    id: uuid.UUID
    document_id: uuid.UUID
    status: str = IngestionStatus.INITIATED
    error_message: Optional[str] = None
    chunks_processed: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Audit columns
    created_by: Optional[uuid.UUID] = None
    created_on: Optional[datetime] = None
    last_updated_by: Optional[uuid.UUID] = None
    last_updated_on: Optional[datetime] = None

    @classmethod
    def from_record(cls, record: dict) -> "IngestionJob":
        """Build an IngestionJob from a database row dict / asyncpg Record."""
        return cls(
            id=record["id"],
            document_id=record["document_id"],
            status=record.get("status", IngestionStatus.INITIATED),
            error_message=record.get("error_message"),
            chunks_processed=record.get("chunks_processed", 0),
            started_at=record.get("started_at"),
            completed_at=record.get("completed_at"),
            created_by=record.get("created_by"),
            created_on=record.get("created_on"),
            last_updated_by=record.get("last_updated_by"),
            last_updated_on=record.get("last_updated_on"),
        )
