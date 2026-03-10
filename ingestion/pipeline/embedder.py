"""
ingestion/pipeline/embedder.py — Text embedding generation.

Purpose:
    Generates vector embeddings for document chunks using a sentence
    transformer model.

Model:
    Default: all-MiniLM-L6-v2 (configurable per tenant via client_configs)

Methods:
    embed(chunks: list[str]) → numpy.ndarray

Notes:
    - Embeddings are normalised for cosine similarity (inner product with FAISS).
    - The embedding model is loaded as a singleton — shared across invocations.
"""
