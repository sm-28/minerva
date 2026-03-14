"""
ingestion/services/ingestion_service.py — Orchestrates the full ingestion pipeline.

Purpose:
    Coordinates the end-to-end document ingestion flow: download from S3,
    parse, chunk, embed, build index, archive old index, update DB.

Methods:
    process_job(job_id: str) → bool

Execution Flow:
    1. Load ingestion job and document record from DB.
    2. Download document file from S3.
    3. Parse document → raw text.
    4. Chunk text → list of chunks.
    5. Embed chunks → numpy array.
    6. Load all OTHER active documents' chunks for this client.
    7. Build combined FAISS index for the client.
    8. Archive the previous vector index to S3.
    9. Save the new index and metadata.
    10. Update document record (chunk_count, embedding_model, vector_index_path).
    11. Update ingestion_jobs status to 'success'.
    12. On any failure: update status to 'failed' with error_message.
"""

from __future__ import annotations

import os
import tempfile
import traceback
import uuid
from datetime import datetime, timezone

import boto3
import numpy as np

from ingestion.pipeline import chunker, embedder, parser, vector_store
from shared.db.connection import get_connection
from shared.db.tenant_context import get_tenant_schema
from shared.exceptions.pipeline_exceptions import IngestionError
from shared.models.document import Document
from shared.models.ingestion_job import IngestionJob, IngestionStatus
from shared.utils.logging import get_logger

logger = get_logger("ingestion.services.ingestion_service")

_S3_BUCKET = os.environ.get("S3_BUCKET", "minerva-documents")
_DEFAULT_EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")


async def process_job(job_id: str) -> bool:
    """
    Run the full ingestion pipeline for a given ingestion job ID.

    Args:
        job_id: UUID string of the ingestion_jobs record.

    Returns:
        True on success, False on failure.
    """
    job_uuid = uuid.UUID(job_id)
    logger.info(f"Starting ingestion for job_id={job_id}")
    temp_file: str | None = None

    try:
        # ── Step 1: Load job and trigger document from DB ─────────────────
        job, document, schema_name, client_id = await _load_job_and_document(job_uuid)
        logger.info(
            f"Loaded job: trigger_document_id={document.id}, "
            f"filename={document.filename}, schema={schema_name}"
        )

        # ── Step 2: Mark job as in_progress ───────────────────────────────
        await _update_job_status(
            job_uuid, IngestionStatus.IN_PROGRESS, schema_name,
            started_at=datetime.now(timezone.utc),
        )

        # ── Step 3: Download document from S3 ─────────────────────────────
        temp_file = await _download_from_s3(document.s3_path, document.filename)
        logger.info(f"Downloaded to {temp_file}")

        # ── Step 4: Parse document → text ─────────────────────────────────
        raw_text = parser.parse(temp_file, document.file_type)

        # ── Step 5: Chunk text ────────────────────────────────────────────
        chunks = chunker.chunk(raw_text)
        chunk_texts = [c["text"] for c in chunks]

        # ── Step 6: Embed current document's chunks ───────────────────────
        current_embeddings = embedder.embed(chunk_texts, model_name=_DEFAULT_EMBEDDING_MODEL)

        # ── Step 7: Load + embed all OTHER active documents for this client ─
        all_embeddings, all_metadata = await _build_combined_embeddings(
            client_id=str(client_id),
            schema_name=schema_name,
            current_doc=document,
            current_chunks=chunks,
            current_embeddings=current_embeddings,
        )

        # ── Step 8: Archive previous index ────────────────────────────────
        vector_store.archive_previous_index(client_id=str(client_id), job_id=job_id)

        # ── Step 9: Build and save new FAISS index ────────────────────────
        faiss_index = vector_store.build_index(all_embeddings, all_metadata)
        index_s3_path = vector_store.save_index(
            faiss_index, all_metadata,
            client_id=str(client_id),
            job_id=job_id,
        )

        # ── Step 10: Update trigger document record ────────────────────────
        await _update_document(
            doc_id=document.id,
            schema_name=schema_name,
            chunk_count=len(chunks),
            embedding_model=_DEFAULT_EMBEDDING_MODEL,
        )

        # ── Step 10b: Update job with all processed document IDs ──────────
        all_doc_ids = list({m["document_id"] for m in all_metadata})
        await _update_job_document_ids(job_uuid, schema_name, all_doc_ids)

        # ── Step 11: Mark job success ─────────────────────────────────────
        await _update_job_status(
            job_uuid, IngestionStatus.SUCCESS, schema_name,
            chunks_processed=len(chunks),
            completed_at=datetime.now(timezone.utc),
        )

        # ── Step 12: Notify Core API to invalidate cache ──────────────────
        await _notify_core_of_index_update(schema_name, client_id)

        logger.info(
            f"Ingestion complete: job_id={job_id}, "
            f"chunks={len(chunks)}, index={index_s3_path}"
        )
        return True

    except Exception as exc:
        error_msg = f"{type(exc).__name__}: {exc}"
        logger.error(
            f"Ingestion failed: job_id={job_id} — {error_msg}",
            exc_info=True,
        )
        # ── Step 12: Mark job failed ──────────────────────────────────────
        try:
            # We need schema_name to update; if we couldn't even load the job
            # we have nothing to update, so guard with a try/except.
            if "schema_name" in dir():  # noqa: SIM102
                await _update_job_status(
                    job_uuid, IngestionStatus.FAILED,
                    schema_name,  # type: ignore[possibly-undefined]
                    error_message=error_msg,
                    completed_at=datetime.now(timezone.utc),
                )
        except Exception:
            logger.error("Could not update job status to failed", exc_info=True)
        return False

    finally:
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)
            logger.debug(f"Cleaned up temporary file: {temp_file}")


# ── Database helpers ──────────────────────────────────────────────────────────

async def _load_job_and_document(
    job_uuid: uuid.UUID,
) -> tuple[IngestionJob, Document, str, uuid.UUID]:
    """
    Load the ingestion job, its trigger document, and the client schema.

    The trigger document is document_ids[0] — the newly uploaded document
    that caused the Dashboard to create this ingestion job.

    Returns:
        (job, trigger_document, schema_name, client_id)
    """
    schema_name = os.environ.get("TENANT_SCHEMA")
    if not schema_name:
        raise IngestionError(
            "load_job",
            "TENANT_SCHEMA environment variable is required for this ECS task.",
        )

    async with get_connection(schema_name) as conn:
        job_row = await conn.fetchrow(
            "SELECT * FROM ingestion_jobs WHERE id = $1", job_uuid
        )
        if not job_row:
            raise IngestionError("load_job", f"Ingestion job not found: {job_uuid}")

        job = IngestionJob.from_record(dict(job_row))

        trigger_doc_id = job.trigger_document_id
        if not trigger_doc_id:
            raise IngestionError(
                "load_job", f"Ingestion job {job_uuid} has no document_ids."
            )

        doc_row = await conn.fetchrow(
            "SELECT * FROM documents WHERE id = $1", trigger_doc_id
        )
        if not doc_row:
            raise IngestionError(
                "load_job", f"Trigger document not found: {trigger_doc_id}"
            )

        document = Document.from_record(dict(doc_row))

        # Fetch the client_id from the public.clients table via schema_name
        client_row = await conn.fetchrow(
            "SELECT id FROM public.clients WHERE schema_name = $1", schema_name
        )
        if not client_row:
            raise IngestionError(
                "load_job",
                f"Could not find client for schema '{schema_name}'",
            )
        client_id: uuid.UUID = client_row["id"]

    return job, document, schema_name, client_id


async def _update_job_status(
    job_id: uuid.UUID,
    status: str,
    schema_name: str,
    *,
    error_message: str | None = None,
    chunks_processed: int | None = None,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
) -> None:
    """Update the ingestion_jobs row with new status and optional fields."""
    fields = ["status = $2", "last_updated_on = $3"]
    values: list = [job_id, status, datetime.now(timezone.utc)]
    idx = 4

    if error_message is not None:
        fields.append(f"error_message = ${idx}")
        values.append(error_message)
        idx += 1
    if chunks_processed is not None:
        fields.append(f"chunks_processed = ${idx}")
        values.append(chunks_processed)
        idx += 1
    if started_at is not None:
        fields.append(f"started_at = ${idx}")
        values.append(started_at)
        idx += 1
    if completed_at is not None:
        fields.append(f"completed_at = ${idx}")
        values.append(completed_at)
        idx += 1

    sql = f"UPDATE ingestion_jobs SET {', '.join(fields)} WHERE id = $1"

    async with get_connection(schema_name) as conn:
        await conn.execute(sql, *values)

    logger.debug(f"Updated job {job_id} status → {status}")


async def _update_document(
    doc_id: uuid.UUID,
    schema_name: str,
    chunk_count: int,
    embedding_model: str,
) -> None:
    """Update the documents row after successful ingestion."""
    async with get_connection(schema_name) as conn:
        await conn.execute(
            """
            UPDATE documents
               SET chunk_count     = $2,
                   embedding_model = $3,
                   last_updated_on = $4
             WHERE id = $1
            """,
            doc_id,
            chunk_count,
            embedding_model,
            datetime.now(timezone.utc),
        )
    logger.debug(f"Updated document {doc_id}: chunk_count={chunk_count}")


async def _update_job_document_ids(
    job_id: uuid.UUID,
    schema_name: str,
    all_doc_ids: list[str],
) -> None:
    """Update the ingestion job with the full list of processed document IDs."""
    doc_uuids = [uuid.UUID(d) if isinstance(d, str) else d for d in all_doc_ids]
    async with get_connection(schema_name) as conn:
        await conn.execute(
            "UPDATE ingestion_jobs SET document_ids = $2 WHERE id = $1",
            job_id,
            doc_uuids,
        )
    logger.debug(f"Updated job {job_id}: document_ids={len(doc_uuids)} documents")


async def _notify_core_of_index_update(schema_name: str, client_id: uuid.UUID) -> None:
    """Broadcasts a cache invalidation event to all active Core tasks via Postgres NOTIFY."""
    async with get_connection(schema_name) as conn:
        # Postgres NOTIFY requires strings for the channel payload
        await conn.execute(f"NOTIFY index_updates, '{str(client_id)}'")
    logger.debug(f"Broadcasted NOTIFY index_updates for client {client_id}")


# ── S3 download helper ────────────────────────────────────────────────────────

async def _download_from_s3(s3_path: str, filename: str) -> str:
    """
    Download a file from S3 to a local temp file and return its path.

    Args:
        s3_path:  Full S3 URI, e.g. 's3://bucket/key/doc.pdf'.
        filename: Original filename (used for extension detection).

    Returns:
        Absolute path to the downloaded temp file.
    """
    if not s3_path.startswith("s3://"):
        raise IngestionError("download", f"Invalid S3 path: '{s3_path}'")

    parts = s3_path[len("s3://"):].split("/", 1)
    if len(parts) != 2:
        raise IngestionError("download", f"Cannot parse S3 path: '{s3_path}'")

    bucket, key = parts
    ext = os.path.splitext(filename)[1] or ".tmp"

    # Use a named tmp file so we preserve the extension for the parser
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=ext)
    os.close(tmp_fd)

    s3 = boto3.client("s3", region_name=os.getenv("AWS_REGION", "me-central-1"))
    try:
        s3.download_file(bucket, key, tmp_path)
    except Exception as exc:
        os.remove(tmp_path)
        raise IngestionError("download", f"S3 download failed: {exc}") from exc

    return tmp_path


# ── Multi-document index builder ──────────────────────────────────────────────

async def _build_combined_embeddings(
    client_id: str,
    schema_name: str,
    current_doc: Document,
    current_chunks: list[dict],
    current_embeddings: np.ndarray,
) -> tuple[np.ndarray, list[dict]]:
    """
    Collect embeddings and metadata for all active documents of the client,
    combining the freshly-embedded current document with re-embedded others.

    Returns:
        (combined_embeddings, combined_metadata)
    """
    all_embeddings: list[np.ndarray] = [current_embeddings]
    all_metadata: list[dict] = [
        {
            **c,
            "document_id": str(current_doc.id),
            "filename": current_doc.filename,
        }
        for c in current_chunks
    ]

    # Fetch all other active documents for this client
    async with get_connection(schema_name) as conn:
        rows = await conn.fetch(
            """
            SELECT id, filename, file_type, s3_path, chunk_count, embedding_model
              FROM documents
             WHERE is_active = true
               AND id != $1
            """,
            current_doc.id,
        )

    for row in rows:
        other_doc = Document.from_record(dict(row))
        if not other_doc.s3_path:
            logger.warning(f"Document {other_doc.id} has no s3_path — skipping.")
            continue

        logger.info(f"Re-embedding document: {other_doc.filename} ({other_doc.id})")
        try:
            tmp_file = await _download_from_s3(other_doc.s3_path, other_doc.filename)
            try:
                text = parser.parse(tmp_file, other_doc.file_type)
                chunks = chunker.chunk(text)
                if not chunks:
                    continue
                embs = embedder.embed(
                    [c["text"] for c in chunks],
                    model_name=_DEFAULT_EMBEDDING_MODEL,
                )
                all_embeddings.append(embs)
                all_metadata.extend(
                    {
                        **c,
                        "document_id": str(other_doc.id),
                        "filename": other_doc.filename,
                    }
                    for c in chunks
                )
            finally:
                if os.path.exists(tmp_file):
                    os.remove(tmp_file)
        except Exception as exc:
            # Non-critical: log and skip this document so others still get indexed
            logger.warning(
                f"Skipping document {other_doc.id} due to error: {exc}"
            )

    combined = np.vstack(all_embeddings).astype(np.float32)
    logger.info(
        f"Combined index: {combined.shape[0]} total chunks "
        f"from {1 + len(rows)} documents"
    )
    return combined, all_metadata
