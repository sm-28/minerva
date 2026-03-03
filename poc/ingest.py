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

BASE_DIR        = Path(__file__).parent
CLIENT_CONFIG   = BASE_DIR / "client_config.json"
DOCS_DIR        = BASE_DIR / "documents"
STORE_DIR       = BASE_DIR / "vector_store"

EMBED_MODEL     = "all-MiniLM-L6-v2"
CHUNK_SIZE      = 600
OVERLAP         = 100

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("ingest")

# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

def extract_text_from_pdf(pdf_path: Path) -> str:
    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)

def clean_text(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"[^\S\n]+\n", "\n", text)
    return text.strip()

# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def split_into_chunks(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = OVERLAP) -> list[str]:
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

def ingest_client(client_name: str, index_name: str, model: SentenceTransformer):
    client_docs_dir = DOCS_DIR / index_name
    client_store_dir = STORE_DIR / index_name
    
    client_store_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = sorted(client_docs_dir.glob("*.pdf"))
    if not pdf_files:
        log.warning(f"No PDF files found for client {client_name} in {client_docs_dir}")
        return

    log.info(f"Processing client {client_name}: {len(pdf_files)} PDF(s)")

    all_chunks = []
    metadata   = []

    for pdf_path in pdf_files:
        log.info(f"  Processing: {pdf_path.name}")
        raw_text   = extract_text_from_pdf(pdf_path)
        clean      = clean_text(raw_text)
        chunks     = split_into_chunks(clean)
        log.info(f"    → {len(chunks)} chunks")

        for idx, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            metadata.append({
                "source":     pdf_path.name,
                "chunk_idx":  idx,
                "text":       chunk,
                "char_count": len(chunk),
            })

    if not all_chunks:
        return

    log.info(f"  Generating embeddings for {len(all_chunks)} chunks...")
    embeddings = model.encode(all_chunks, show_progress_bar=True, normalize_embeddings=True)
    embeddings = np.array(embeddings, dtype="float32")

    dim   = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    index_path = client_store_dir / "index.faiss"
    chunks_path = client_store_dir / "chunks.json"
    
    faiss.write_index(index, str(index_path))
    with open(chunks_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    log.info(f"  Saved index → {index_path}")
    log.info(f"  Saved metadata → {chunks_path}")

def main():
    if not CLIENT_CONFIG.exists():
        log.error(f"Client config not found: {CLIENT_CONFIG}")
        sys.exit(1)

    with open(CLIENT_CONFIG) as f:
        clients = json.load(f)

    log.info(f"Loading embedding model '{EMBED_MODEL}'...")
    model = SentenceTransformer(EMBED_MODEL)

    for client_data in clients:
        ingest_client(client_data["Client"], client_data["index"], model)

    log.info("Ingestion complete ✓")

if __name__ == "__main__":
    main()
