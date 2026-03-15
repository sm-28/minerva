"""
ingestion — Minerva's document processing service.

Processes uploaded documents into vector embeddings for RAG retrieval.
Runs as an ECS task triggered by the dashboard on document upload.

Deployment: ECS (min 0, max 2 tasks — triggered on demand).
"""
