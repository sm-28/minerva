"""
shared/models/business_api_key.py — Business-scoped API key pair model.

Table: public.business_api_keys

Fields:
    id, business_id (FK → businesses.id), api_key, api_secret_hash, is_active

Business Rules:
    - API keys are scoped to a specific Business (not the Organization).
    - Maximum 2 active keys per business.
    - api_secret is stored as a bcrypt hash — the plaintext is never persisted.
    - Supports key rotation without downtime:
        1. Generate new key pair → integrate into client backend.
        2. Deactivate old key pair once migrated.
    - The api_key resolves directly to a business_id at runtime, which determines
      the active tenant schema, FAISS index, and configuration.
"""
