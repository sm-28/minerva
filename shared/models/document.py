"""
shared/models/document.py — Document model (merged with version tracking).

Table: tenant_<slug>.documents

Fields:
    id, filename, file_type, s3_path, version, is_active,
    chunk_count, embedding_model

Notes:
    - Only one version per document should have is_active=true at any time.
    - Old versions and their S3 files are retained for audit.
    - One FAISS vector index exists per Business (built from all active documents).
    - Document S3 paths are scoped per Business:
        s3://{bucket}/businesses/{business_id}/docs/{filename}
    - The vector index path is deterministic:
        s3://{bucket}/businesses/{business_id}/index/
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
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
            created_by=record.get("created_by"),
            created_on=record.get("created_on"),
            last_updated_by=record.get("last_updated_by"),
            last_updated_on=record.get("last_updated_on"),
        )
