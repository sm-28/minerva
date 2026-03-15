"""
ingestion/pipeline/vector_store.py — Vector index management.

Purpose:
    Creates, updates, and archives FAISS vector indexes for RAG retrieval.

Methods:
    build_index(embeddings, metadata) → faiss.Index
    save_index(index, metadata, business_id, job_id)
    archive_previous_index(business_id, job_id)
    load_index(business_id) → (faiss.Index, list[dict])

Storage Strategy:
    - One vector index per business containing all active document chunks.
    - Active index stored at a well-known S3 path per business.
    - Prior indexes archived to S3 under: s3://bucket/businesses/{business_id}/archives/{job_id}/
    - Chunk metadata stored alongside the index as JSON.

Notes:
    - When any document version changes, the entire business index is rebuilt
      from all currently active documents.
"""

from __future__ import annotations

import io
import json
import os
import tempfile
import uuid

import boto3
import faiss  # type: ignore
import numpy as np

from shared.exceptions.pipeline_exceptions import IngestionError
from shared.utils.logging import get_logger

logger = get_logger("ingestion.pipeline.vector_store")

_S3_BUCKET = os.environ.get("S3_BUCKET", "minerva-documents")
_INDEX_FILENAME = "faiss.index"
_META_FILENAME = "chunk_metadata.json"


# ── Public API ────────────────────────────────────────────────────────────────

def build_index(embeddings: np.ndarray, metadata: list[dict]) -> faiss.Index:
    """
    Build a FAISS inner-product index from L2-normalised embeddings.

    Args:
        embeddings: float32 array of shape (n_chunks, embedding_dim).
        metadata:   List of dicts (one per chunk), e.g.:
                    [{"text": "...", "chunk_idx": 0, "document_id": "...",
                      "filename": "..."}, ...]

    Returns:
        A trained and populated faiss.IndexFlatIP index.

    Raises:
        IngestionError: If embeddings array is empty or dimension mismatch.
    """
    if embeddings.ndim != 2 or embeddings.shape[0] == 0:
        raise IngestionError("vector_store", "Embeddings array must be 2-D and non-empty.")
    if len(metadata) != embeddings.shape[0]:
        raise IngestionError(
            "vector_store",
            f"metadata length ({len(metadata)}) != embeddings rows ({embeddings.shape[0]})",
        )

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)  # Inner product ≡ cosine for L2-normalised vectors
    index.add(embeddings)

    logger.info(f"Built FAISS index: {index.ntotal} vectors, dim={dim}")
    return index


def save_index(
    index: faiss.Index,
    metadata: list[dict],
    business_id: str,
    job_id: str,
) -> str:
    """
    Serialise and upload the FAISS index + metadata JSON to S3.

    The active index is stored at:
        s3://<bucket>/businesses/<business_id>/index/<_INDEX_FILENAME>
        s3://<bucket>/businesses/<business_id>/index/<_META_FILENAME>

    Args:
        index:       Populated FAISS index.
        metadata:    Chunk metadata list (must match index order).
        business_id: UUID string of the business.
        job_id:      UUID string of the ingestion job (for logging).

    Returns:
        The S3 path prefix for the saved index.
    """
    prefix = _active_index_prefix(business_id)

    with tempfile.TemporaryDirectory() as tmpdir:
        index_path = os.path.join(tmpdir, _INDEX_FILENAME)
        meta_path = os.path.join(tmpdir, _META_FILENAME)

        faiss.write_index(index, index_path)

        with open(meta_path, "w", encoding="utf-8") as fh:
            json.dump(metadata, fh)

        s3 = _get_s3_client()
        s3.upload_file(index_path, _S3_BUCKET, f"{prefix}/{_INDEX_FILENAME}")
        s3.upload_file(meta_path, _S3_BUCKET, f"{prefix}/{_META_FILENAME}")

    s3_path = f"s3://{_S3_BUCKET}/{prefix}"
    logger.info(f"Saved vector index to {s3_path} (job_id={job_id})")
    return s3_path


def archive_previous_index(business_id: str, job_id: str) -> None:
    """
    Copy the current active index to an archive path before overwriting.

    Archive path:
        s3://<bucket>/businesses/<business_id>/archives/<job_id>/

    Args:
        business_id: UUID string of the business.
        job_id:      UUID string of the ingestion job (used as archive folder).
    """
    s3 = _get_s3_client()
    active_prefix = _active_index_prefix(business_id)
    archive_prefix = _archive_index_prefix(business_id, job_id)

    for filename in (_INDEX_FILENAME, _META_FILENAME):
        src_key = f"{active_prefix}/{filename}"
        dst_key = f"{archive_prefix}/{filename}"
        try:
            s3.copy_object(
                Bucket=_S3_BUCKET,
                CopySource={"Bucket": _S3_BUCKET, "Key": src_key},
                Key=dst_key,
            )
            logger.info(f"Archived {src_key} → {dst_key}")
        except s3.exceptions.NoSuchKey:  # type: ignore[attr-defined]
            logger.info(f"No existing index to archive at {src_key} — skipping.")
        except Exception as exc:
            # Fatal: if we can't archive, something is wrong with S3/config.
            raise IngestionError(f"Failed to archive {src_key}: {exc}") from exc


def load_index(business_id: str) -> tuple[faiss.Index, list[dict]]:
    """
    Download and deserialise the active FAISS index for a business.

    Args:
        business_id: UUID string of the business.

    Returns:
        (index, metadata) tuple.

    Raises:
        IngestionError: If the index does not exist in S3.
    """
    prefix = _active_index_prefix(business_id)
    s3 = _get_s3_client()

    with tempfile.TemporaryDirectory() as tmpdir:
        index_path = os.path.join(tmpdir, _INDEX_FILENAME)
        meta_path = os.path.join(tmpdir, _META_FILENAME)

        try:
            s3.download_file(_S3_BUCKET, f"{prefix}/{_INDEX_FILENAME}", index_path)
            s3.download_file(_S3_BUCKET, f"{prefix}/{_META_FILENAME}", meta_path)
        except Exception as exc:
            raise IngestionError(
                "vector_store",
                f"Failed to download index for business {business_id}: {exc}",
            ) from exc

        index = faiss.read_index(index_path)
        with open(meta_path, "r", encoding="utf-8") as fh:
            metadata = json.load(fh)

    logger.info(
        f"Loaded FAISS index for business {business_id}: "
        f"{index.ntotal} vectors, {len(metadata)} metadata entries"
    )
    return index, metadata


# ── Helpers ───────────────────────────────────────────────────────────────────

def _active_index_prefix(business_id: str) -> str:
    return f"businesses/{business_id}/index"


def _archive_index_prefix(business_id: str, job_id: str) -> str:
    return f"businesses/{business_id}/archives/{job_id}"


def _get_s3_client():
    """Return a boto3 S3 client (uses AWS credential chain)."""
    return boto3.client(
        "s3",
        region_name=os.getenv("AWS_REGION", "me-central-1"),
    )
