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

from __future__ import annotations

import numpy as np

from shared.exceptions.pipeline_exceptions import IngestionError
from shared.utils.logging import get_logger

logger = get_logger("ingestion.pipeline.embedder")

DEFAULT_MODEL = "all-MiniLM-L6-v2"

# Singleton cache: model_name → SentenceTransformer instance
_model_cache: dict[str, object] = {}


def _get_model(model_name: str):
    """Load (or retrieve from cache) a SentenceTransformer model."""
    if model_name in _model_cache:
        return _model_cache[model_name]

    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
    except ImportError as exc:
        raise IngestionError(
            "embed",
            "sentence-transformers is not installed. "
            "Run: pip install sentence-transformers",
        ) from exc

    logger.info(f"Loading embedding model: {model_name}")
    model = SentenceTransformer(model_name)
    _model_cache[model_name] = model
    logger.info(f"Embedding model '{model_name}' loaded and cached.")
    return model


def embed(
    chunks: list[str],
    model_name: str = DEFAULT_MODEL,
    batch_size: int = 64,
) -> np.ndarray:
    """
    Generate L2-normalised embeddings for a list of text chunks.

    Args:
        chunks:     List of text strings to embed.
        model_name: SentenceTransformer model identifier.
        batch_size: Number of chunks to encode in a single GPU/CPU pass.

    Returns:
        float32 numpy array of shape (len(chunks), embedding_dim).
        Vectors are L2-normalised for use with FAISS inner product search.

    Raises:
        IngestionError: If sentence-transformers is not installed or encoding fails.
        ValueError:     If chunks is empty.
    """
    if not chunks:
        raise ValueError("embed() received an empty chunks list.")

    model = _get_model(model_name)

    logger.info(f"Embedding {len(chunks)} chunks with model '{model_name}'")
    try:
        embeddings: np.ndarray = model.encode(  # type: ignore[attr-defined]
            chunks,
            batch_size=batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,  # L2 normalise for cosine via inner product
            convert_to_numpy=True,
        )
    except Exception as exc:
        raise IngestionError("embed", f"Embedding failed: {exc}") from exc

    logger.info(f"Generated embeddings: shape={embeddings.shape}")
    return embeddings.astype(np.float32)
