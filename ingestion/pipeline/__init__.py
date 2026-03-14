"""
ingestion.pipeline — Document processing pipeline steps.

Exposes:
    parser       — text extraction from documents
    chunker      — sliding-window word chunking
    embedder     — SentenceTransformer embedding generation
    vector_store — FAISS index build/save/load/archive
"""

from ingestion.pipeline import chunker, embedder, parser, vector_store

__all__ = ["parser", "chunker", "embedder", "vector_store"]
