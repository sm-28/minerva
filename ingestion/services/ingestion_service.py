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
