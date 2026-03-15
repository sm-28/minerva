"""
core/pipelines/components/rag_component.py — Retrieval-Augmented Generation component.

Purpose:
    Retrieves relevant document chunks from the vector store based on the
    user's query. Determines if the query can be answered from available
    knowledge. This is a NON-CRITICAL component — on failure, the LLM
    proceeds with empty context.

Input (from context):
    context.translated_text (or context.transcript if no translation)
    context.client_id — to identify which vector index to search

Output (to context):
    context.rag_chunks  — list of dicts with keys: rank, text, source, score
    context.is_unknown  — True if top chunk score below threshold

Notes:
    - One vector index exists per client (not per document).
    - Uses the embedding model singleton for query encoding.
"""
