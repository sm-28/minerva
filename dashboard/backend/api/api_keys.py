"""
dashboard/backend/api/api_keys.py — API key management endpoints.

Purpose:
    Allows client admins to generate, rotate, and revoke API key pairs.

Endpoints:
    POST   /api/v1/admin/clients/{cid}/api-keys          — Generate new key pair
    GET    /api/v1/admin/clients/{cid}/api-keys           — List active keys
    DELETE /api/v1/admin/clients/{cid}/api-keys/{key_id}  — Revoke a key

Business Rules:
    - Maximum 2 active api_key pairs per client at any time.
    - When generating a new pair, the api_secret is shown ONCE in the
      response and stored as a bcrypt hash. It cannot be retrieved later.
    - Key rotation: generate new pair → migrate backend → revoke old pair.
"""
