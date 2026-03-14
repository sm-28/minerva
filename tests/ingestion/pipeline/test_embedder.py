"""
tests/ingestion/pipeline/test_embedder.py — Unit tests for the embedder.

Covers:
    - embed() returns correct numpy shape
    - Embeddings are L2-normalised (unit vectors)
    - Singleton model caching (model loaded once)
    - Empty chunks list raises ValueError
    - IngestionError raised when sentence-transformers not installed
    - Batch processing does not change output shape
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


class TestEmbedShape:
    def test_embed_returns_2d_array(self, sample_chunks):
        """Integration test — requires sentence-transformers installed."""
        pytest.importorskip("sentence_transformers")

        from ingestion.pipeline.embedder import embed

        texts = [c["text"] for c in sample_chunks]
        result = embed(texts)
        assert result.ndim == 2
        assert result.shape[0] == len(texts)

    def test_embed_returns_float32(self, sample_chunks):
        pytest.importorskip("sentence_transformers")

        from ingestion.pipeline.embedder import embed

        texts = [c["text"] for c in sample_chunks]
        result = embed(texts)
        assert result.dtype == np.float32

    def test_embed_vectors_are_normalised(self, sample_chunks):
        """L2 norm of each embedding should be ~1.0."""
        pytest.importorskip("sentence_transformers")

        from ingestion.pipeline.embedder import embed

        texts = [c["text"] for c in sample_chunks]
        result = embed(texts)
        norms = np.linalg.norm(result, axis=1)
        np.testing.assert_allclose(norms, np.ones(len(texts)), atol=1e-5)


class TestEmbedValidation:
    def test_empty_chunks_raises_value_error(self):
        from ingestion.pipeline.embedder import embed

        with pytest.raises(ValueError, match="empty"):
            embed([])

    def test_single_chunk_works(self):
        pytest.importorskip("sentence_transformers")

        from ingestion.pipeline.embedder import embed

        result = embed(["Single sentence for embedding."])
        assert result.shape[0] == 1


class TestEmbedModelCache:
    def test_model_loaded_once_for_same_name(self, sample_chunks):
        """The model singleton should only be loaded once."""
        pytest.importorskip("sentence_transformers")

        import ingestion.pipeline.embedder as emb_mod

        # Clear cache for fresh test
        emb_mod._model_cache.clear()

        texts = [c["text"] for c in sample_chunks]
        emb_mod.embed(texts)
        emb_mod.embed(texts)

        assert len(emb_mod._model_cache) == 1


class TestEmbedMissingLibrary:
    def test_import_error_raises_ingestion_error(self, sample_chunks):
        """When sentence-transformers is not importable, IngestionError is raised."""
        import ingestion.pipeline.embedder as emb_mod
        from shared.exceptions.pipeline_exceptions import IngestionError

        # Temporarily hide sentence_transformers
        original = emb_mod._model_cache.copy()
        emb_mod._model_cache.clear()

        saved = sys.modules.pop("sentence_transformers", None)

        # Also mock builtins.__import__ to raise ImportError for sentence_transformers
        real_import = __builtins__.__import__ if hasattr(__builtins__, "__import__") else __import__

        def fake_import(name, *args, **kwargs):
            if name == "sentence_transformers":
                raise ImportError("Mocked missing sentence_transformers")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import):
            with pytest.raises(IngestionError, match="sentence-transformers"):
                emb_mod._get_model("all-MiniLM-L6-v2")

        # Restore
        if saved:
            sys.modules["sentence_transformers"] = saved
        emb_mod._model_cache.update(original)
