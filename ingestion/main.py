"""
ingestion/main.py — ECS task entry point for the Ingestion service.

Purpose:
    Entry point for the ingestion ECS task. Receives an ingestion job ID,
    reads job details from the database, processes the document, and
    updates the job status.

Intended Usage:
    python -m ingestion.main --job-id <ingestion_job_id>

Execution Flow:
    1. Receive ingestion_job_id from command argument or environment variable.
    2. Read ingestion job details from the database (document_id, tenant schema).
    3. Update job status to 'in_progress'.
    4. Download the document from S3.
    5. Run the ingestion pipeline: Parse → Chunk → Embed → Store.
    6. Update the documents record with chunk_count, embedding_model, vector_index_path.
    7. Archive prior vector index to S3 under folder named with job ID.
    8. Update job status to 'success' (or 'failed' with error_message).

Notes:
    - The task exits after processing. It does not run as a long-lived service.
    - One vector index exists per client, rebuilt with all active documents.
"""
