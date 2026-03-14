"""
tests/ — Test suite for the Minerva ingestion pipeline.

Structure:
    tests/
    ├── conftest.py                        — shared fixtures
    ├── ingestion/
    │   ├── pipeline/
    │   │   ├── test_parser.py            — document text extraction tests
    │   │   ├── test_chunker.py           — text chunking tests
    │   │   ├── test_embedder.py          — embedding generation tests
    │   │   └── test_vector_store.py      — FAISS index management tests
    │   └── services/
    │       └── test_ingestion_service.py — end-to-end orchestration tests
    └── shared/
        ├── test_db_connection.py         — DB pool tests
        ├── test_tenant_context.py        — schema routing tests
        └── test_exceptions.py            — custom exception tests
"""
