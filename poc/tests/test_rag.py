import unittest
from unittest.mock import patch, MagicMock, mock_open
import numpy as np
import sys
import os

# Ensure the poc directory is in the path so we can import rag
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from rag import retrieve, build_rag_prompt, UNKNOWN_THRESHOLD

class TestRAGRetrieval(unittest.TestCase):

    @patch("rag.load_vector_store")
    @patch("rag._get_embed_model")
    def test_retrieve_success(self, mock_get_model, mock_load):
        # Setup mocks
        mock_index = MagicMock()
        mock_metadata = [{"text": "Sample text", "source": "test.pdf", "chunk_idx": 0}]
        mock_load.return_value = (mock_index, mock_metadata)
        
        # Mock index.search returns (scores, indices)
        # We simulate a high similarity score (0.9) which is > UNKNOWN_THRESHOLD (0.35)
        mock_index.search.return_value = (np.array([[0.9]]), np.array([[0]]))
        mock_index.ntotal = 1
        
        mock_model = MagicMock()
        mock_get_model.return_value = mock_model
        mock_model.encode.return_value = np.array([[0.1] * 384]) # dummy vector
        
        # Execute
        results = retrieve("test query", top_k=1)
        
        # Assert
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["text"], "Sample text")
        self.assertFalse(results[0]["is_unknown"])
        self.assertAlmostEqual(results[0]["score"], 0.9)

    @patch("rag.load_vector_store")
    @patch("rag._get_embed_model")
    def test_retrieve_unknown(self, mock_get_model, mock_load):
        # Setup mocks
        mock_index = MagicMock()
        mock_metadata = [{"text": "Sample text", "source": "test.pdf", "chunk_idx": 0}]
        mock_load.return_value = (mock_index, mock_metadata)
        
        # Mock index.search with a low similarity score (0.2) which is < UNKNOWN_THRESHOLD (0.35)
        mock_index.search.return_value = (np.array([[0.2]]), np.array([[0]]))
        mock_index.ntotal = 1
        
        mock_model = MagicMock()
        mock_get_model.return_value = mock_model
        mock_model.encode.return_value = np.array([[0.1] * 384])
        
        # Execute
        results = retrieve("unknown query", top_k=1)
        
        # Assert
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0]["is_unknown"])
        self.assertAlmostEqual(results[0]["score"], 0.2)

    def test_build_rag_prompt(self):
        chunks = [
            {"rank": 1, "text": "Hello world", "score": 0.8},
            {"rank": 2, "text": "Foo bar", "score": 0.7}
        ]
        query = "What is the meaning of life?"
        
        prompt = build_rag_prompt(chunks, query)
        
        self.assertIn("Hello world", prompt)
        self.assertIn("Foo bar", prompt)
        self.assertIn("What is the meaning of life?", prompt)
        self.assertTrue(prompt.startswith("Context:"))
        self.assertIn("Question:", prompt)

if __name__ == "__main__":
    unittest.main()
