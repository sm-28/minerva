"""
shared/models/document.py — Document model (merged with version tracking).

Table: tenant_<slug>.documents

Fields:
    id, filename, file_type, s3_path, version, is_active,
    chunk_count, embedding_model, vector_index_path,
    ingestion_job_id (FK → ingestion_jobs), uploaded_by (FK → users)

Notes:
    - Only one version per document should have is_active=true at any time.
    - Old versions and their S3 files are retained for audit.
    - One vector index exists per client (built from all active documents).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Document:
    """
    Represents a row in tenant_<slug>.documents.

    All timestamps are stored as UTC-aware datetimes.
    """

    id: uuid.UUID
    filename: str
    file_type: str                          # e.g. 'pdf', 'docx', 'txt'
    s3_path: str                            # e.g. 's3://bucket/tenant/docs/uuid.pdf'
    version: int = 1
    is_active: bool = True
    chunk_count: Optional[int] = None
    embedding_model: Optional[str] = None   # e.g. 'all-MiniLM-L6-v2'
    vector_index_path: Optional[str] = None # e.g. 's3://bucket/tenant/index/faiss.index'
    ingestion_job_id: Optional[uuid.UUID] = None
    uploaded_by: Optional[uuid.UUID] = None

    # Audit columns
    created_by: Optional[uuid.UUID] = None
    created_on: Optional[datetime] = None
    last_updated_by: Optional[uuid.UUID] = None
    last_updated_on: Optional[datetime] = None

    @classmethod
    def from_record(cls, record: dict) -> "Document":
        """Build a Document from a database row dict / asyncpg Record."""
        return cls(
            id=record["id"],
            filename=record["filename"],
            file_type=record.get("file_type", "pdf"),
            s3_path=record["s3_path"],
            version=record.get("version", 1),
            is_active=record.get("is_active", True),
            chunk_count=record.get("chunk_count"),
            embedding_model=record.get("embedding_model"),
            vector_index_path=record.get("vector_index_path"),
            ingestion_job_id=record.get("ingestion_job_id"),
            uploaded_by=record.get("uploaded_by"),
            created_by=record.get("created_by"),
            created_on=record.get("created_on"),
            last_updated_by=record.get("last_updated_by"),
            last_updated_on=record.get("last_updated_on"),
        )
