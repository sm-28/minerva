"""
ingestion/pipeline/vector_store.py — Vector index management.

Purpose:
    Creates, updates, and archives FAISS vector indexes for RAG retrieval.

Methods:
    build_index(embeddings, metadata) → faiss.Index
    save_index(index, metadata, client_id, job_id)
    archive_previous_index(client_id, job_id)
    load_index(client_id) → (faiss.Index, list[dict])

Storage Strategy:
    - One vector index per client containing all active document chunks.
    - Active index stored at a well-known S3 path per client.
    - Prior indexes archived to S3 under: s3://bucket/archives/{job_id}/
    - Chunk metadata stored alongside the index as JSON.

Notes:
    - When any document version changes, the entire client index is rebuilt
      from all currently active documents.
"""
