"""
dashboard/backend/api/settings.py — Configuration management endpoints.

Purpose:
    Manage client-specific configurations and global system settings.

Endpoints:
    GET    /api/v1/admin/clients/{cid}/configs          — List all configs
    PUT    /api/v1/admin/clients/{cid}/configs/{key}    — Update a config value
    GET    /api/v1/admin/system-settings                — List system settings
    PUT    /api/v1/admin/system-settings/{key}          — Update a system setting

Common Config Keys:
    pipeline_components, default_language, goal_definition,
    provider_overrides, greeting_template, unknown_response_template,
    voice_config

Notes:
    - Changes are written to the database. Core picks them up on its
      next ConfigCache refresh cycle (every 5 minutes).
    - For urgent changes, optionally call Core's /internal/cache/refresh.
"""
