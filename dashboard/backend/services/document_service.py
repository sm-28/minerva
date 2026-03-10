"""
dashboard/backend/services/document_service.py — Document management business logic.

Purpose:
    Handles document uploads to S3, version management (is_active flag),
    and ingestion job record creation.

Methods:
    upload_document(client_id, file, filename) → Document
    upload_new_version(document_id, file) → Document
    list_documents(client_id, include_inactive) → list[Document]
    get_document(document_id) → Document

Version Management:
    - New upload: version=1, is_active=true.
    - Re-upload: previous active version set to is_active=false,
      new record created with version+1, is_active=true.
    - Old document files are retained in S3 for audit.
"""
