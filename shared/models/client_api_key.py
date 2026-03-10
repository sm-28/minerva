"""
shared/models/client_api_key.py — API key pair model.

Table: public.client_api_keys

Fields:
    id, client_id (FK → clients), api_key, api_secret_hash, is_active

Business Rules:
    - Maximum 2 active keys per client.
    - api_secret is stored as a bcrypt hash.
    - Supports key rotation without downtime.
"""
