"""
shared/models/ingestion_job.py — Ingestion job model.

Table: tenant_<slug>.ingestion_jobs

Fields:
    id, document_id (FK → documents),
    status ('initiated' | 'in_progress' | 'success' | 'failed'),
    error_message, chunks_processed, started_at, completed_at
"""
