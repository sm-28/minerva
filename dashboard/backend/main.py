"""
dashboard/backend/main.py — FastAPI entry point for the Dashboard backend.

Purpose:
    Serves the admin API for client management, document uploads,
    configuration, analytics, API key management, and ingestion triggers.

Intended Usage:
    Run via uvicorn:
        uvicorn dashboard.backend.main:app --host 0.0.0.0 --port 8001

Responsibilities:
    - Register API routers for all admin operations
    - Authenticate dashboard users (admin/viewer roles)
    - Serve as the control plane — does NOT handle end-user conversations

Notes:
    - Dashboard does not communicate with Core directly.
    - Configuration changes are written to the database and picked up
      by Core's ConfigCache on its next refresh cycle (every 5 minutes).
"""
