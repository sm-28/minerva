"""
dashboard/backend/api/documents.py — Document upload and version management.

Purpose:
    Handles document uploads, version tracking, and triggers ingestion.

Endpoints:
    POST   /api/v1/admin/clients/{cid}/documents       — Upload a new document
    GET    /api/v1/admin/clients/{cid}/documents       — List documents (all versions)
    GET    /api/v1/admin/clients/{cid}/documents/{id}  — Get document details
    POST   /api/v1/admin/clients/{cid}/documents/{id}/reupload — Upload new version

Upload Flow:
    1. Store document file in S3.
    2. Create a documents record (version=1 or increment, is_active=true).
    3. Set previous active version to is_active=false.
    4. Create an ingestion_jobs record with status='initiated'.
    5. Trigger the ECS ingestion task with the ingestion job ID.
"""
