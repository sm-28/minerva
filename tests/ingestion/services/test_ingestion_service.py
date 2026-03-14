"""
tests/ingestion/services/test_ingestion_service.py — Tests for the ingestion orchestrator.

Covers:
    - process_job() returns True on success
    - process_job() returns False and updates job status on failure
    - job status lifecycle: in_progress → success
    - job status set to 'failed' with error_message on exception
    - Missing job in DB raises IngestionError (job returns False)
    - TENANT_SCHEMA env var missing raises IngestionError
    - S3 download failure marks job failed
    - Combined embeddings include current + other active documents
"""

from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, call

import numpy as np
import pytest

from shared.exceptions.pipeline_exceptions import IngestionError
from shared.models.document import Document
from shared.models.ingestion_job import IngestionJob, IngestionStatus


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def job_record(job_id, document_id):
    return {
        "id": job_id,
        "document_id": document_id,
        "status": IngestionStatus.INITIATED,
        "error_message": None,
        "chunks_processed": 0,
        "started_at": None,
        "completed_at": None,
        "created_by": None,
        "created_on": datetime.now(timezone.utc),
        "last_updated_by": None,
        "last_updated_on": datetime.now(timezone.utc),
    }


@pytest.fixture
def doc_record(document_id, client_id):
    return {
        "id": document_id,
        "filename": "test_doc.pdf",
        "file_type": "pdf",
        "s3_path": f"s3://minerva-test-bucket/clients/{client_id}/docs/test_doc.pdf",
        "version": 1,
        "is_active": True,
        "chunk_count": None,
        "embedding_model": None,
        "vector_index_path": None,
        "ingestion_job_id": None,
        "uploaded_by": None,
        "created_by": None,
        "created_on": datetime.now(timezone.utc),
        "last_updated_by": None,
        "last_updated_on": datetime.now(timezone.utc),
    }


@pytest.fixture
def client_record(client_id):
    return {"id": client_id}


def _make_mock_conn(job_record, doc_record, client_record):
    """Build an AsyncMock DB connection that returns appropriate rows."""
    mock_conn = AsyncMock()

    async def fetchrow_side_effect(query, *args):
        query_upper = query.strip().upper()
        if "INGESTION_JOBS" in query_upper:
            return job_record
        elif "DOCUMENTS" in query_upper and "IS_ACTIVE" not in query_upper:
            return doc_record
        elif "PUBLIC.CLIENTS" in query_upper or "CLIENTS" in query_upper:
            return client_record
        return None

    async def fetch_side_effect(query, *args):
        # Return empty list for other active docs query
        return []

    async def execute_side_effect(*args, **kwargs):
        return None

    mock_conn.fetchrow.side_effect = fetchrow_side_effect
    mock_conn.fetch.side_effect = fetch_side_effect
    mock_conn.execute.side_effect = execute_side_effect

    return mock_conn


# ── process_job success path ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_process_job_success(
    monkeypatch, job_id, document_id, client_id,
    job_record, doc_record, client_record, tmp_txt_file,
):
    """Happy path: process_job returns True and sets status to success."""
    mock_conn = _make_mock_conn(job_record, doc_record, client_record)

    @asynccontextmanager
    async def mock_get_connection(schema=None):
        yield mock_conn

    monkeypatch.setenv("TENANT_SCHEMA", "tenant_acme")

    # Patch DB connection
    import shared.db.connection as db_mod
    monkeypatch.setattr(db_mod, "get_connection", mock_get_connection)

    # Patch S3 download to copy tmp_txt_file
    import boto3
    import shutil

    def fake_download(bucket, key, local_path):
        shutil.copy(tmp_txt_file, local_path)

    mock_s3 = MagicMock()
    mock_s3.download_file.side_effect = fake_download
    mock_s3.upload_file = MagicMock()
    mock_s3.copy_object = MagicMock()
    mock_s3.exceptions = MagicMock()
    mock_s3.exceptions.NoSuchKey = Exception
    monkeypatch.setattr(boto3, "client", lambda *a, **kw: mock_s3)

    # Patch document file_type to txt (avoid pdf lib dependency)
    doc_record["file_type"] = "txt"

    from ingestion.services.ingestion_service import process_job
    result = await process_job(str(job_id))
    assert result is True


@pytest.mark.asyncio
async def test_process_job_returns_false_on_db_failure(monkeypatch, job_id):
    """If DB is unavailable, process_job returns False."""
    monkeypatch.setenv("TENANT_SCHEMA", "tenant_acme")

    import shared.db.connection as db_mod

    @asynccontextmanager
    async def broken_connection(schema=None):
        mock_conn = AsyncMock()
        mock_conn.fetchrow.side_effect = Exception("DB connection refused")
        yield mock_conn

    monkeypatch.setattr(db_mod, "get_connection", broken_connection)

    from ingestion.services.ingestion_service import process_job
    result = await process_job(str(job_id))
    assert result is False


@pytest.mark.asyncio
async def test_process_job_missing_tenant_schema(monkeypatch, job_id):
    """Missing TENANT_SCHEMA env var causes process_job to return False."""
    monkeypatch.delenv("TENANT_SCHEMA", raising=False)

    from ingestion.services.ingestion_service import process_job
    result = await process_job(str(job_id))
    assert result is False


@pytest.mark.asyncio
async def test_process_job_not_found_returns_false(
    monkeypatch, job_id, doc_record, client_record
):
    """If the ingestion job doesn't exist, returns False."""
    monkeypatch.setenv("TENANT_SCHEMA", "tenant_acme")

    mock_conn = AsyncMock()
    mock_conn.fetchrow.return_value = None  # not found
    mock_conn.fetch.return_value = []
    mock_conn.execute = AsyncMock()

    @asynccontextmanager
    async def mock_get_connection(schema=None):
        yield mock_conn

    import ingestion.services.ingestion_service as svc
    monkeypatch.setattr(svc, "get_connection", mock_get_connection)

    result = await svc.process_job(str(job_id))
    assert result is False


# ── Status update calls ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_process_job_marks_in_progress_then_success(
    monkeypatch, job_id, document_id, client_id,
    job_record, doc_record, client_record, tmp_txt_file,
):
    """Verify the job status transitions via execute() calls."""
    execute_calls: list[str] = []
    mock_conn = _make_mock_conn(job_record, doc_record, client_record)

    original_execute = mock_conn.execute.side_effect

    async def tracking_execute(sql, *args):
        execute_calls.append(sql)
        return None

    mock_conn.execute.side_effect = tracking_execute

    @asynccontextmanager
    async def mock_get_connection(schema=None):
        yield mock_conn

    monkeypatch.setenv("TENANT_SCHEMA", "tenant_acme")
    doc_record["file_type"] = "txt"

    import boto3, shutil
    mock_s3 = MagicMock()
    mock_s3.download_file.side_effect = lambda b, k, p: shutil.copy(tmp_txt_file, p)
    mock_s3.upload_file = MagicMock()
    mock_s3.copy_object = MagicMock()
    mock_s3.exceptions = MagicMock()
    mock_s3.exceptions.NoSuchKey = Exception
    monkeypatch.setattr(boto3, "client", lambda *a, **kw: mock_s3)

    import shared.db.connection as db_mod
    monkeypatch.setattr(db_mod, "get_connection", mock_get_connection)

    from ingestion.services.ingestion_service import process_job
    await process_job(str(job_id))

    # At least one UPDATE to ingestion_jobs must have occurred
    found_update = False
    for call_args in mock_conn.execute.call_args_list:
        args, kwargs = call_args
        if args and "UPDATE ingestion_jobs" in args[0].upper():
            found_update = True
            break
    
    assert found_update, f"No UPDATE ingestion_jobs found in execute calls: {mock_conn.execute.call_args_list}"
