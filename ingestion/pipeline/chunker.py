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

from __future__ import annotations

from shared.utils.logging import get_logger

logger = get_logger("ingestion.pipeline.chunker")

DEFAULT_CHUNK_SIZE = 600   # words per chunk
DEFAULT_OVERLAP = 100      # word overlap between chunks


def chunk(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[dict]:
    """
    Split text into overlapping word-based chunks.

    Args:
        text:       Full document text (post-parsing, pre-embedding).
        chunk_size: Target number of words per chunk.
        overlap:    Number of words shared between consecutive chunks.

    Returns:
        List of chunk dicts, each with keys:
            - text       (str)
            - chunk_idx  (int)
            - char_count (int)

    Raises:
        ValueError: If chunk_size <= 0 or overlap >= chunk_size.
    """
    if chunk_size <= 0:
        raise ValueError(f"chunk_size must be > 0, got {chunk_size}")
    if overlap >= chunk_size:
        raise ValueError(
            f"overlap ({overlap}) must be less than chunk_size ({chunk_size})"
        )

    words = text.split()
    if not words:
        logger.warning("chunker received empty text — returning empty list")
        return []

    step = chunk_size - overlap
    chunks: list[dict] = []
    chunk_idx = 0

    for start in range(0, len(words), step):
        word_slice = words[start : start + chunk_size]
        if not word_slice:
            break

        chunk_text = " ".join(word_slice)
        chunks.append(
            {
                "text": chunk_text,
                "chunk_idx": chunk_idx,
                "char_count": len(chunk_text),
            }
        )
        chunk_idx += 1

        # If we captured the last words, stop
        if start + chunk_size >= len(words):
            break

    logger.info(
        f"Chunked document into {len(chunks)} chunks "
        f"(chunk_size={chunk_size}, overlap={overlap})"
    )
    return chunks
