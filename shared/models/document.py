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
