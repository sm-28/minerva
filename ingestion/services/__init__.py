"""
ingestion.services — Business logic for ingestion operations.

Exposes:
    ingestion_service.process_job(job_id) — orchestrates the full pipeline
"""

from ingestion.services.ingestion_service import process_job

__all__ = ["process_job"]
