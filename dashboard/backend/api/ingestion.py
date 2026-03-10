"""
dashboard/backend/api/ingestion.py — Ingestion job monitoring endpoints.

Purpose:
    Provides status polling for ingestion jobs. The dashboard UI polls
    this endpoint every 5 seconds to track processing progress.

Endpoints:
    GET /api/v1/admin/ingestion/{job_id}  — Get ingestion job status
    GET /api/v1/admin/ingestion           — List recent ingestion jobs

Response Fields:
    status           — initiated | in_progress | success | failed
    chunks_processed — number of chunks processed so far
    error_message    — error details if status is 'failed'
    started_at       — when processing began
    completed_at     — when processing finished
"""
