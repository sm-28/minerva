"""
tests/conftest.py — Shared pytest fixtures for the Minerva test suite.
"""

from __future__ import annotations

import os
import tempfile
import uuid
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest


# ── Environment defaults ──────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def set_env_defaults(monkeypatch):
    """Ensure required environment variables are set for all tests."""
    defaults = {
        "DB_HOST": "localhost",
        "DB_PORT": "5432",
        "DB_NAME": "minerva_test",
        "DB_USER": "minerva",
        "DB_PASSWORD": "test_password",
        "S3_BUCKET": "minerva-test-bucket",
        "AWS_REGION": "ap-south-1",
        "TENANT_SCHEMA": "tenant_acme",
        "INGESTION_JOB_ID": str(uuid.uuid4()),
        "EMBEDDING_MODEL": "all-MiniLM-L6-v2",
        "ENV": "test",
    }
    for key, val in defaults.items():
        monkeypatch.setenv(key, val)


# ── Common IDs ────────────────────────────────────────────────────────────────

@pytest.fixture
def client_id() -> uuid.UUID:
    return uuid.UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture
def document_id() -> uuid.UUID:
    return uuid.UUID("22222222-2222-2222-2222-222222222222")


@pytest.fixture
def job_id() -> uuid.UUID:
    return uuid.UUID("33333333-3333-3333-3333-333333333333")


# ── Document fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def sample_text() -> str:
    return (
        "Minerva is a modular AI conversation platform. "
        "It supports PDF, DOCX, and TXT document ingestion. "
        "Documents are parsed, chunked, embedded, and stored in FAISS. "
        "Each client has a dedicated vector index containing all active documents. "
        "The platform is deployed on AWS ECS with RDS and S3 for storage. "
        "Tenants are isolated via PostgreSQL schema-per-tenant architecture. "
        "The ingestion pipeline runs as an ECS task triggered on document upload. "
        "Embeddings are generated using sentence-transformers and normalised for cosine similarity. "
        "Prior vector indexes are archived to S3 under a folder named with the job ID."
    )


@pytest.fixture
def sample_chunks(sample_text) -> list[dict]:
    """Pre-computed chunks from sample_text for unit tests."""
    from ingestion.pipeline.chunker import chunk
    return chunk(sample_text, chunk_size=20, overlap=5)


@pytest.fixture
def sample_embeddings(sample_chunks) -> np.ndarray:
    """Synthetic float32 embeddings matching sample_chunks count."""
    n = len(sample_chunks)
    rng = np.random.default_rng(42)
    embs = rng.random((n, 384)).astype(np.float32)
    # L2 normalise
    norms = np.linalg.norm(embs, axis=1, keepdims=True)
    return embs / norms


# ── Temporary file helpers ────────────────────────────────────────────────────

@pytest.fixture
def tmp_txt_file(sample_text) -> str:
    """Write sample_text to a temp .txt file; yield path; cleanup."""
    fd, path = tempfile.mkstemp(suffix=".txt")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(sample_text)
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def tmp_pdf_file() -> str:
    """Create a minimal valid PDF temp file using reportlab (if available)."""
    try:
        from reportlab.lib.pagesizes import letter  # type: ignore
        from reportlab.pdfgen import canvas  # type: ignore

        fd, path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        c = canvas.Canvas(path, pagesize=letter)
        c.drawString(72, 720, "Minerva test PDF document.")
        c.drawString(72, 700, "This document is used for parser unit tests.")
        c.save()
        yield path
        if os.path.exists(path):
            os.remove(path)
    except ImportError:
        pytest.skip("reportlab not installed — skipping PDF fixture")


# ── S3 mock ───────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_s3(monkeypatch):
    """
    Replace boto3.client('s3', ...) with a MagicMock so tests don't hit AWS.
    """
    import boto3

    mock_client = MagicMock()
    mock_client.upload_file = MagicMock()
    mock_client.download_file = MagicMock()
    mock_client.copy_object = MagicMock()
    mock_client.exceptions = MagicMock()
    mock_client.exceptions.NoSuchKey = Exception

    monkeypatch.setattr(boto3, "client", lambda *args, **kwargs: mock_client)
    return mock_client


# ── DB mock ───────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_db_connection(monkeypatch):
    """
    Mock shared.db.connection.get_connection so tests skip real DB calls.
    """
    from contextlib import asynccontextmanager

    mock_conn = AsyncMock()

    @asynccontextmanager
    async def _mock_get_connection(schema=None):
        yield mock_conn

    import shared.db.connection as db_mod
    monkeypatch.setattr(db_mod, "get_connection", _mock_get_connection)
    return mock_conn
