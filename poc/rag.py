"""
rag.py — Retrieval-Augmented Generation utilities for Audiobot POC.

Loads the FAISS index persisted by ingest.py and exposes:
    load_vector_store() -> (index, metadata)
    retrieve(query, top_k)  -> list of chunk dicts with scores
    compute_similarity_score(query, chunk) -> float
"""

import json
from pathlib import Path

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

from utils import get_logger

logger = get_logger("rag")

# ---------------------------------------------------------------------------
# Paths and constants
# ---------------------------------------------------------------------------

BASE_DIR   = Path(__file__).parent
INDEX_PATH = BASE_DIR / "vector_store" / "index.faiss"
CHUNKS_PATH= BASE_DIR / "vector_store" / "chunks.json"

EMBED_MODEL       = "all-MiniLM-L6-v2"
UNKNOWN_THRESHOLD = 0.35   # cosine similarity below this → UNKNOWN (all-MiniLM-L6-v2 typical range is 0.3–0.5 for related content)

# Module-level singletons (lazy-loaded)
_index    = None
_metadata = None
_model    = None


# ---------------------------------------------------------------------------
# Load / init
# ---------------------------------------------------------------------------

def load_vector_store():
    """
    Load the FAISS index and chunk metadata from disk.
    Returns (faiss.Index, list[dict]) or raises FileNotFoundError.
    """
    global _index, _metadata, _model

    if _index is not None:
        return _index, _metadata

    if not INDEX_PATH.exists():
        raise FileNotFoundError(
            f"Vector store not found at {INDEX_PATH}. "
            "Run `python ingest.py` first."
        )

    logger.info("Loading FAISS index from %s", INDEX_PATH)
    _index = faiss.read_index(str(INDEX_PATH))

    with open(CHUNKS_PATH, encoding="utf-8") as f:
        _metadata = json.load(f)

    logger.info("Index loaded: %d vectors", _index.ntotal)
    _model = _get_embed_model()
    return _index, _metadata


def _get_embed_model() -> SentenceTransformer:
    """Return (cached) embedding model."""
    global _model
    if _model is None:
        logger.info("Loading embedding model '%s'", EMBED_MODEL)
        _model = SentenceTransformer(EMBED_MODEL)
    return _model


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

def retrieve(query: str, top_k: int = 3) -> list[dict]:
    """
    Retrieve the top-k most similar document chunks for *query*.

    Each returned dict has:
        text         str   — chunk text
        source       str   — originating PDF filename
        chunk_idx    int   — chunk position in that document
        score        float — cosine similarity  (0 … 1)
        is_unknown   bool  — True if score < UNKNOWN_THRESHOLD

    The first element's is_unknown flag drives the global UNKNOWN logic.
    """
    index, metadata = load_vector_store()
    model           = _get_embed_model()

    # Embed and normalise query
    q_vec = model.encode([query], normalize_embeddings=True).astype("float32")

    top_k_actual = min(top_k, index.ntotal)
    scores, indices = index.search(q_vec, top_k_actual)

    results = []
    for rank, (score, idx) in enumerate(zip(scores[0], indices[0])):
        if idx < 0:
            continue          # FAISS returns -1 for empty slots
        chunk_meta = metadata[idx]
        results.append({
            "rank":       rank + 1,
            "text":       chunk_meta["text"],
            "source":     chunk_meta.get("source", "unknown"),
            "chunk_idx":  chunk_meta.get("chunk_idx", idx),
            "score":      float(score),
            "is_unknown": float(score) < UNKNOWN_THRESHOLD,
        })

    if results:
        top_score = results[0]["score"]
        logger.info(
            "Retrieve: top score=%.3f (%s) for query %r",
            top_score,
            "UNKNOWN" if results[0]["is_unknown"] else "KNOWN",
            query[:60],
        )

    return results


def compute_similarity_score(query: str, chunk_text: str) -> float:
    """
    Compute cosine similarity between a query and a single chunk.
    Useful for standalone evaluation.
    """
    model = _get_embed_model()
    vecs  = model.encode([query, chunk_text], normalize_embeddings=True)
    score = float(np.dot(vecs[0], vecs[1]))
    return score


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = ('''
   If the user sends a greeting like hi, hello, or good morning, respond politely and initiate the conversation by asking whether they need information about our fintech services or our warehousing services. 
   1. You must answer ONLY using the provided context.
   2. If the answer is not present in the context, clearly say: "I do not have that information in the provided documents."
   3. Do not fabricate or infer beyond the context.
   4. Do not add assumptions.
   5. If the retrived content is more than 50 words, summarise it and answer in 20 words
   6. Respond strictly in first person (as if you represent the company speaking directly, e.g., "We provide..." or "I can tell you..."). Never use third person.
   7. 
    Speech Formatting Rules (VERY IMPORTANT):
    - Respond in natural spoken English, as if talking on a phone call.
    - Remove unnecessary trailing zeros (e.g., 11.00 → 11).
    - Avoid special characters literally.
    - Use short, clear sentences suitable for voice.
    - Do not sound like you are reading from a document.

    Tone:
    - Professional
    - Calm
    - Trustworthy
    - Clear and easy to understand
''')

UNKNOWN_RESPONSE = (
    "I do not have information about that in the provided documents. "
    "I have noted your question and can arrange a follow-up."
)


def build_rag_prompt(retrieved_chunks: list[dict], user_query: str) -> str:
    """Assemble the user-prompt from retrieved context chunks."""
    context_parts = [f"[Chunk {c['rank']} | score={c['score']:.3f}]\n{c['text']}" for c in retrieved_chunks]
    context = "\n\n".join(context_parts)
    return (
        f"Context:\n{context}\n\n"
        f"Question:\n{user_query}\n\n"
    )
