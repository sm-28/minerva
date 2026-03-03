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
STORE_DIR  = BASE_DIR / "vector_store"

EMBED_MODEL       = "all-MiniLM-L6-v2"
UNKNOWN_THRESHOLD = 0.20

# Module-level caches
_indices    = {}  # {index_name: faiss.Index}
_metadatas  = {}  # {index_name: list[dict]}
_model      = None

# ---------------------------------------------------------------------------
# Load / init
# ---------------------------------------------------------------------------

def load_vector_store(index_name: str):
    """
    Load the FAISS index and chunk metadata for a specific index_name.
    """
    global _indices, _metadatas, _model

    if index_name in _indices:
        return _indices[index_name], _metadatas[index_name]

    index_path = STORE_DIR / index_name / "index.faiss"
    chunks_path = STORE_DIR / index_name / "chunks.json"

    if not index_path.exists():
        raise FileNotFoundError(
            f"Vector store for '{index_name}' not found at {index_path}. "
            f"Please ensure it is ingested."
        )

    index = faiss.read_index(str(index_path))

    with open(chunks_path, encoding="utf-8") as f:
        metadata = json.load(f)

    _indices[index_name] = index
    _metadatas[index_name] = metadata
    
    if _model is None:
        _model = _get_embed_model()
        
    return index, metadata


def _get_embed_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBED_MODEL)
    return _model


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

def retrieve(query: str, index_name: str, top_k: int = 3) -> list[dict]:
    """
    Retrieve the top-k most similar document chunks for *query* from *index_name*.
    """
    try:
        index, metadata = load_vector_store(index_name)
    except FileNotFoundError:
        return []
        
    model = _get_embed_model()

    # Embed and normalise query
    q_vec = model.encode([query], normalize_embeddings=True).astype("float32")

    top_k_actual = min(top_k, index.ntotal)
    if top_k_actual == 0:
        return []
        
    scores, indices = index.search(q_vec, top_k_actual)
    
    results = []
    for rank, (score, idx) in enumerate(zip(scores[0], indices[0])):
        if idx < 0:
            continue
        chunk_meta = metadata[idx]
        is_unk = float(score) < UNKNOWN_THRESHOLD
        
        results.append({
            "rank":       rank + 1,
            "text":       chunk_meta["text"],
            "source":     chunk_meta.get("source", "unknown"),
            "chunk_idx":  chunk_meta.get("chunk_idx", idx),
            "score":      float(score),
            "is_unknown": is_unk,
        })
    return results


def compute_similarity_score(query: str, chunk_text: str) -> float:
    model = _get_embed_model()
    vecs  = model.encode([query, chunk_text], normalize_embeddings=True)
    score = float(np.dot(vecs[0], vecs[1]))
    return score


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = ('''
   1. You must answer ONLY using the provided context.
   2. If the answer is not present in the context, clearly say: "I do not have that information in the provided documents."
   3. Do not fabricate or infer beyond the context.
   4. Do not add assumptions.
   5. If the retrived content is more than 50 words, summarise it and answer in 20 words
   6. Respond strictly in first person (as if you represent the company speaking directly, e.g., "We provide..." or "I can tell you..."). Never use third person.

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
    context_parts = [f"[Chunk {c['rank']} | score={c['score']:.3f}]\n{c['text']}" for c in retrieved_chunks]
    context = "\n\n".join(context_parts)
    return (
        f"Context:\n{context}\n\n"
        f"Question:\n{user_query}\n\n"
    )
