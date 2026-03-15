"""
tests/ingestion/pipeline/test_vector_store.py — Unit tests for vector store.

Covers:
    - build_index() creates FAISS index with correct ntotal
    - build_index() raises IngestionError on empty/bad embeddings
    - build_index() raises IngestionError on metadata length mismatch
    - save_index() calls S3 upload correctly
    - archive_previous_index() calls S3 copy
    - archive_previous_index() handles missing existing index gracefully
    - load_index() reads index + metadata from S3
    - load_index() raises IngestionError on S3 failure
"""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from unittest.mock import MagicMock, patch, call

import numpy as np
import pytest

faiss = pytest.importorskip("faiss", reason="faiss not installed")

from ingestion.pipeline.vector_store import (
    build_index,
    save_index,
    archive_previous_index,
    load_index,
    _active_index_prefix,
    _archive_index_prefix,
)
from shared.exceptions.pipeline_exceptions import IngestionError


@pytest.fixture
def embeddings_3x4() -> np.ndarray:
    """3 L2-normalised vectors of dim 4."""
    rng = np.random.default_rng(0)
    e = rng.random((3, 4)).astype(np.float32)
    return e / np.linalg.norm(e, axis=1, keepdims=True)


@pytest.fixture
def metadata_3() -> list[dict]:
    return [
        {"text": f"chunk {i}", "chunk_idx": i, "document_id": "doc-1"}
        for i in range(3)
    ]


# ── build_index ───────────────────────────────────────────────────────────────

class TestBuildIndex:
    def test_returns_faiss_index(self, embeddings_3x4, metadata_3):
        index = build_index(embeddings_3x4, metadata_3)
        assert index.ntotal == 3
        assert index.d == 4

    def test_empty_embeddings_raises(self, metadata_3):
        empty = np.zeros((0, 4), dtype=np.float32)
        with pytest.raises(IngestionError, match="non-empty"):
            build_index(empty, metadata_3)

    def test_1d_embeddings_raises(self, metadata_3):
        bad = np.ones((4,), dtype=np.float32)
        with pytest.raises(IngestionError, match="2-D"):
            build_index(bad, metadata_3)

    def test_metadata_length_mismatch_raises(self, embeddings_3x4):
        with pytest.raises(IngestionError, match="metadata length"):
            build_index(embeddings_3x4, [{"text": "only one"}])

    def test_inner_product_index_type(self, embeddings_3x4, metadata_3):
        index = build_index(embeddings_3x4, metadata_3)
        assert isinstance(index, faiss.IndexFlatIP)


# ── save_index ────────────────────────────────────────────────────────────────

class TestSaveIndex:
    def test_uploads_two_files_to_s3(self, embeddings_3x4, metadata_3, mock_s3):
        index = build_index(embeddings_3x4, metadata_3)
        business_id = str(uuid.uuid4())
        job_id = str(uuid.uuid4())

        result = save_index(index, metadata_3, business_id, job_id)

        assert mock_s3.upload_file.call_count == 2
        assert result.startswith("s3://")

    def test_returns_correct_s3_path(self, embeddings_3x4, metadata_3, mock_s3):
        index = build_index(embeddings_3x4, metadata_3)
        business_id = "abc123"
        job_id = "job456"

        result = save_index(index, metadata_3, business_id, job_id)

        assert f"businesses/{business_id}/index" in result


# ── archive_previous_index ────────────────────────────────────────────────────

class TestArchivePreviousIndex:
    def test_copies_both_files(self, mock_s3):
        business_id = "business-1"
        job_id = "job-1"
        archive_previous_index(business_id, job_id)
        assert mock_s3.copy_object.call_count == 2

    def test_no_such_key_does_not_raise(self, mock_s3):
        mock_s3.copy_object.side_effect = mock_s3.exceptions.NoSuchKey
        # Should not raise — just logs a warning
        archive_previous_index("client-1", "job-1")

    def test_generic_exception_does_not_raise(self, mock_s3):
        mock_s3.copy_object.side_effect = Exception("Network error")
        # Should log warning, not raise
        archive_previous_index("client-1", "job-1")


# ── load_index ────────────────────────────────────────────────────────────────

class TestLoadIndex:
    def test_load_raises_on_s3_failure(self, mock_s3):
        mock_s3.download_file.side_effect = Exception("S3 not found")
        with pytest.raises(IngestionError, match="Failed to download"):
            load_index("business-1")

    def test_load_returns_index_and_metadata(self, embeddings_3x4, metadata_3, monkeypatch):
        """
        Save a real index to a tempdir and mock S3 download to use that dir.
        """
        # Build and write index to temp files
        index = build_index(embeddings_3x4, metadata_3)
        tmpdir = tempfile.mkdtemp()
        index_file = os.path.join(tmpdir, "faiss.index")
        meta_file = os.path.join(tmpdir, "chunk_metadata.json")
        faiss.write_index(index, index_file)
        with open(meta_file, "w") as fh:
            json.dump(metadata_3, fh)

        # Patch boto3 download_file to copy from our tmpdir
        def fake_download(bucket, key, local_path):
            if key.endswith("faiss.index"):
                import shutil
                shutil.copy(index_file, local_path)
            elif key.endswith("chunk_metadata.json"):
                import shutil
                shutil.copy(meta_file, local_path)

        import boto3
        mock_client = MagicMock()
        mock_client.download_file.side_effect = fake_download
        monkeypatch.setattr(boto3, "client", lambda *a, **kw: mock_client)

        loaded_index, loaded_meta = load_index("business-1")
        assert loaded_index.ntotal == 3
        assert len(loaded_meta) == 3


# ── Path helpers ──────────────────────────────────────────────────────────────

class TestPathHelpers:
    def test_active_prefix(self):
        assert _active_index_prefix("abc") == "businesses/abc/index"

    def test_archive_prefix(self):
        assert _archive_index_prefix("abc", "job1") == "businesses/abc/archives/job1"
