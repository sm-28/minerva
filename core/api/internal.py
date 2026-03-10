"""
core/api/internal.py — Internal-only endpoints (not publicly accessible).

Purpose:
    Provides operational endpoints accessible only within the VPC.
    These are NOT exposed through the public ALB.

Endpoints:
    POST /internal/cache/refresh — Force the ConfigCache singleton to
         reload all configuration from the database immediately.
         Called by the dashboard after critical config changes.

    GET  /internal/health        — Health check for ALB target group.
         Returns 200 if the service is operational.

Security:
    These endpoints must be restricted to internal network access only
    (VPC security group rules). No JWT required.
"""
