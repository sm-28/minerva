"""
shared/models/ingestion_job.py — Ingestion job model.

Table: tenant_<slug>.ingestion_jobs

Fields:
    id, document_ids (UUID[] — all active documents processed in this job),
    status ('initiated' | 'in_progress' | 'success' | 'failed'),
    error_message, chunks_processed, started_at, completed_at

Notes:
    - document_ids is initialised with the trigger document UUID by the Dashboard.
    - The ingestion pipeline updates document_ids to include ALL active documents
      that were re-embedded as part of the full index rebuild.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
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
    document_ids: list[uuid.UUID] = field(default_factory=list)
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

    @property
    def trigger_document_id(self) -> Optional[uuid.UUID]:
        """The first document in the list is the one that triggered the job."""
        return self.document_ids[0] if self.document_ids else None

    @classmethod
    def from_record(cls, record: dict) -> "IngestionJob":
        """Build an IngestionJob from a database row dict / asyncpg Record."""
        raw_ids = record.get("document_ids", [])
        # asyncpg returns UUIDs directly; handle both UUID and str
        doc_ids = [
            uid if isinstance(uid, uuid.UUID) else uuid.UUID(uid)
            for uid in (raw_ids or [])
        ]
        return cls(
            id=record["id"],
            document_ids=doc_ids,
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
