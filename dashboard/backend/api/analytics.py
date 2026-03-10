"""
dashboard/backend/api/analytics.py — Analytics and reporting endpoints.

Purpose:
    Provides aggregated data for the dashboard analytics views.

Endpoints:
    GET /api/v1/admin/clients/{cid}/analytics/sessions   — Session counts and trends
    GET /api/v1/admin/clients/{cid}/analytics/usage       — Usage/cost summaries
    GET /api/v1/admin/clients/{cid}/analytics/unknowns    — Unknown query analysis
    GET /api/v1/admin/clients/{cid}/analytics/feedback    — Feedback/satisfaction data

Notes:
    - All queries run against the tenant schema for proper isolation.
    - Consider materialized views or pre-aggregation for performance.
"""
