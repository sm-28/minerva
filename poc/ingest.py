"""
ingest.py — Document ingestion pipeline for Audiobot POC.

Usage:
    python ingest.py

Reads all PDF files from ./documents/, extracts and cleans text,
chunks it with overlap, generates sentence-transformer embeddings,
and persists a FAISS index + chunk metadata JSON to ./vector_store/.
"""

import os
import json
import re
import sys
import logging
from pathlib import Path

import numpy as np
import pdfplumber
import faiss
from sentence_transformers import SentenceTransformer

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_DIR      = Path(__file__).parent
DOCS_DIR      = BASE_DIR / "documents"
STORE_DIR     = BASE_DIR / "vector_store"
INDEX_PATH    = STORE_DIR / "index.faiss"
CHUNKS_PATH   = STORE_DIR / "chunks.json"

EMBED_MODEL   = "all-MiniLM-L6-v2"   # fast, good quality, 384-dim
CHUNK_SIZE    = 600                    # target tokens (~words) per chunk
OVERLAP       = 100                    # tokens overlap between chunks

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("ingest")


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract raw text from all pages of a PDF."""
    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
            log.debug("  Page %d: %d chars", i + 1, len(page_text or ""))
    return "\n".join(text_parts)


def clean_text(text: str) -> str:
    """Remove excessive whitespace and artefacts from extracted text."""
    text = re.sub(r"\n{3,}", "\n\n", text)          # collapse multiple blank lines
    text = re.sub(r"[ \t]{2,}", " ", text)           # collapse horizontal whitespace
    text = re.sub(r"[^\S\n]+\n", "\n", text)         # trailing spaces before newline
    return text.strip()


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def split_into_chunks(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = OVERLAP) -> list[str]:
    """
    Split text into overlapping chunks by approximate word count.
    Tries to honour sentence boundaries where possible.
    """
    # Tokenise roughly by whitespace
    words = text.split()
    if not words:
        return []

    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        if end == len(words):
            break
        start += chunk_size - overlap

    return chunks


# ---------------------------------------------------------------------------
# Ingestion pipeline
# ---------------------------------------------------------------------------

def ingest():
    """Main ingestion routine."""
    STORE_DIR.mkdir(parents=True, exist_ok=True)

    # Find PDFs
    pdf_files = sorted(DOCS_DIR.glob("*.pdf"))
    if not pdf_files:
        log.warning(
            "No PDF files found in %s. "
            "Drop one or more PDFs there and re-run this script.",
            DOCS_DIR
        )
        sys.exit(0)

    log.info("Found %d PDF(s): %s", len(pdf_files), [p.name for p in pdf_files])

    # Extract and chunk
    all_chunks = []
    metadata   = []

    for pdf_path in pdf_files:
        log.info("Processing: %s", pdf_path.name)
        raw_text   = extract_text_from_pdf(pdf_path)
        clean      = clean_text(raw_text)
        chunks     = split_into_chunks(clean)
        log.info("  → %d chunks", len(chunks))

        for idx, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            metadata.append({
                "source":     pdf_path.name,
                "chunk_idx":  idx,
                "text":       chunk,
                "char_count": len(chunk),
            })

    log.info("Total chunks: %d", len(all_chunks))

    # Generate embeddings
    log.info("Loading embedding model '%s' …", EMBED_MODEL)
    model = SentenceTransformer(EMBED_MODEL)
    log.info("Generating embeddings …")
    embeddings = model.encode(all_chunks, show_progress_bar=True, normalize_embeddings=True)
    embeddings = np.array(embeddings, dtype="float32")

    # Build FAISS index
    dim   = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)   # inner product = cosine similarity (with L2-normalised vectors)
    index.add(embeddings)
    log.info("FAISS index: %d vectors, dim=%d", index.ntotal, dim)

    # Persist
    faiss.write_index(index, str(INDEX_PATH))
    with open(CHUNKS_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    log.info("Saved index → %s", INDEX_PATH)
    log.info("Saved metadata → %s", CHUNKS_PATH)
    log.info("Ingestion complete ✓")


if __name__ == "__main__":
    ingest()
