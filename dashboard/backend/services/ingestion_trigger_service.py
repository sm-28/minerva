"""
dashboard/backend/services/ingestion_trigger_service.py — ECS ingestion task trigger.

Purpose:
    Triggers the ECS ingestion task when a document is uploaded or
    re-uploaded. Passes the ingestion job ID to the task.

Methods:
    trigger_ingestion(ingestion_job_id) → bool

Implementation:
    Uses AWS ECS RunTask API to launch an ingestion task with the
    job ID as an environment variable or command argument. The
    ingestion task reads job details from the database.

Notes:
    - Ingestion ECS tasks scale from min=0 to max=2.
    - The task is ephemeral — it processes the job and exits.
"""
