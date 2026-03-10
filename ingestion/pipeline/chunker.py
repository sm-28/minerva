"""
ingestion/pipeline/chunker.py — Text chunking for embedding.

Purpose:
    Splits extracted text into overlapping chunks suitable for embedding
    and vector search.

Configuration:
    chunk_size  — target words per chunk (default: 600)
    overlap     — word overlap between consecutive chunks (default: 100)

Methods:
    chunk(text: str, chunk_size: int, overlap: int) → list[dict]

Each chunk dict contains:
    text       — the chunk text
    chunk_idx  — position in the document
    char_count — character count
"""
