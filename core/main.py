"""
core/main.py — FastAPI application entry point for the Core service.

Purpose:
    Initialises the FastAPI app, registers API routers, sets up middleware
    (JWT auth, tenant context, CORS), and starts the ConfigCache background
    refresh thread.

Intended Usage:
    Run via uvicorn:
        uvicorn core.main:app --host 0.0.0.0 --port 8000

    In Docker/ECS, this is the container entrypoint.

Responsibilities:
    - Create the FastAPI application instance
    - Register routers from core.api (auth, sessions, internal)
    - Attach AuthMiddleware for JWT validation
    - Initialise ConfigCache singleton on startup
    - Initialise ProviderResolver singleton on startup
    - Initialise database connection pool on startup
    - Graceful shutdown hooks for cleanup
"""
