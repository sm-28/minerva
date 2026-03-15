"""
core — Minerva's runtime conversation engine.

This package contains the FastAPI application that handles all real-time
user conversations across channels (web, WhatsApp, phone). It owns the
pipeline execution, session management, and message processing.

Deployment: ECS with ALB sticky sessions (min 2, max 5 tasks).
"""
