"""
core/api/auth.py — Authentication endpoint.

Purpose:
    Handles the B2B token exchange flow. The client's backend calls this
    endpoint with their api_key + api_secret to obtain a JWT for their
    end-customer.

Endpoint:
    POST /api/v1/auth/token

Request Body:
    {
        "api_key": "client-api-key",
        "api_secret": "client-api-secret",
        "customer_identifier": "end-user-id-from-client-system"
    }

Validation Steps:
    1. Verify api_key exists in client_api_keys table and is active.
    2. Verify api_secret matches the stored bcrypt hash.
    3. Verify the request origin IP is in the client's allowed_ips list.
    4. Verify the request Origin/Referer domain is in allowed_domains.
    5. Create a new session record in the tenant schema.
    6. Generate a JWT (30-min TTL) containing client_id, session_id,
       tenant schema name, and customer_identifier.

Response:
    { "token": "eyJ...", "session_id": "uuid", "expires_in": 1800 }

Security:
    - api_key/api_secret never reach the end-customer's browser.
    - The returned JWT is the only credential stored client-side (as a cookie).
    - Clients can have a maximum of 2 active api_key pairs for rotation.
"""
