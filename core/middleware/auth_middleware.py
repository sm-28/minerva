"""
core/middleware/auth_middleware.py — JWT authentication middleware.

Purpose:
    Intercepts every incoming request (except /auth/token and /internal/*),
    validates the JWT token from the cookie or Authorization header,
    and injects tenant context into the request state.

Responsibilities:
    1. Extract the JWT from the 'minerva_token' cookie or
       'Authorization: Bearer <token>' header.
    2. Decode and validate the JWT (signature, expiry).
    3. Extract client_id, session_id, and tenant schema from claims.
    4. Set request.state.client_id, request.state.session_id,
       request.state.tenant_schema for downstream handlers.
    5. Implement sliding window token refresh: if the token is within
       5 minutes of expiry and the request is valid, issue a new token
       with a refreshed 30-minute TTL and set it in the response cookie.

Error Handling:
    - Missing token: 401 Unauthorized
    - Expired token: 401 Unauthorized with 'token_expired' error code
    - Invalid token: 401 Unauthorized
"""
