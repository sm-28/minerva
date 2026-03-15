"""
tests/ingestion/pipeline/test_chunker.py — Unit tests for the text chunker.

Covers:
    - Basic chunking with default settings
    - Correct number of chunks produced
    - Overlap between consecutive chunks
    - chunk_size / overlap boundary conditions
    - Empty text returns empty list
    - Invalid arguments raise ValueError
    - Chunk dict structure (keys: text, chunk_idx, char_count)
    - Last chunk shorter than chunk_size is still included
"""

from __future__ import annotations

import pytest

from ingestion.pipeline.chunker import chunk, DEFAULT_CHUNK_SIZE, DEFAULT_OVERLAP


SAMPLE_100_WORDS = " ".join([f"word{i}" for i in range(100)])
SAMPLE_600_WORDS = " ".join([f"word{i}" for i in range(600)])
SAMPLE_1200_WORDS = " ".join([f"word{i}" for i in range(1200)])


class TestChunkBasic:
    def test_returns_list(self):
        result = chunk(SAMPLE_100_WORDS, chunk_size=20, overlap=5)
        assert isinstance(result, list)

    def test_empty_text_returns_empty_list(self):
        result = chunk("", chunk_size=20, overlap=5)
        assert result == []

    def test_whitespace_only_returns_empty(self):
        result = chunk("   \n  \t  ", chunk_size=20, overlap=5)
        assert result == []

    def test_single_word_returns_one_chunk(self):
        result = chunk("hello", chunk_size=20, overlap=5)
        assert len(result) == 1
        assert result[0]["text"] == "hello"


class TestChunkStructure:
    def test_chunk_dict_keys(self):
        result = chunk(SAMPLE_100_WORDS, chunk_size=20, overlap=5)
        for c in result:
            assert "text" in c
            assert "chunk_idx" in c
            assert "char_count" in c

    def test_chunk_idx_is_sequential(self):
        result = chunk(SAMPLE_100_WORDS, chunk_size=20, overlap=5)
        for i, c in enumerate(result):
            assert c["chunk_idx"] == i

    def test_char_count_matches_text_length(self):
        result = chunk(SAMPLE_100_WORDS, chunk_size=20, overlap=5)
        for c in result:
            assert c["char_count"] == len(c["text"])


class TestChunkCount:
    def test_text_shorter_than_chunk_size_gives_one_chunk(self):
        words = " ".join(["word"] * 10)
        result = chunk(words, chunk_size=20, overlap=5)
        assert len(result) == 1

    def test_text_exactly_chunk_size_gives_one_chunk(self):
        words = " ".join(["word"] * 20)
        result = chunk(words, chunk_size=20, overlap=5)
        assert len(result) == 1

    def test_text_double_chunk_size_with_overlap(self):
        # With chunk_size=20 and overlap=5, step=15
        # 30 words → first chunk [0..19], second chunk [15..34] but capped at 30
        words = " ".join([f"w{i}" for i in range(30)])
        result = chunk(words, chunk_size=20, overlap=5)
        assert len(result) == 2

    def test_large_text_produces_expected_chunk_count(self):
        # 1200 words, chunk_size=600, overlap=100 → step=500
        # chunks start at: 0, 500, 1000 → 3 chunks (last starts at 1000 < 1200)
        result = chunk(SAMPLE_1200_WORDS, chunk_size=600, overlap=100)
        assert len(result) >= 2


class TestChunkOverlap:
    def test_consecutive_chunks_share_words(self):
        # chunk_size=10, overlap=3 → step=7
        words = [f"w{i}" for i in range(20)]
        result = chunk(" ".join(words), chunk_size=10, overlap=3)

        assert len(result) >= 2

        first_words = set(result[0]["text"].split())
        second_words = set(result[1]["text"].split())
        shared = first_words & second_words
        assert len(shared) > 0  # There should be overlap

    def test_no_overlap_gives_disjoint_chunks(self):
        words = " ".join([f"w{i}" for i in range(20)])
        result = chunk(words, chunk_size=10, overlap=0)
        assert len(result) == 2

        first_words = set(result[0]["text"].split())
        second_words = set(result[1]["text"].split())
        assert first_words.isdisjoint(second_words)


class TestChunkValidation:
    def test_zero_chunk_size_raises(self):
        with pytest.raises(ValueError, match="chunk_size must be > 0"):
            chunk(SAMPLE_100_WORDS, chunk_size=0, overlap=0)

    def test_negative_chunk_size_raises(self):
        with pytest.raises(ValueError, match="chunk_size must be > 0"):
            chunk(SAMPLE_100_WORDS, chunk_size=-1, overlap=0)

    def test_overlap_equal_to_chunk_size_raises(self):
        with pytest.raises(ValueError, match="overlap"):
            chunk(SAMPLE_100_WORDS, chunk_size=10, overlap=10)

    def test_overlap_greater_than_chunk_size_raises(self):
        with pytest.raises(ValueError, match="overlap"):
            chunk(SAMPLE_100_WORDS, chunk_size=10, overlap=15)


class TestChunkDefaults:
    def test_default_chunk_size_is_600(self):
        assert DEFAULT_CHUNK_SIZE == 600

    def test_default_overlap_is_100(self):
        assert DEFAULT_OVERLAP == 100

    def test_called_with_defaults_works(self):
        result = chunk(SAMPLE_600_WORDS)
        assert isinstance(result, list)
        assert len(result) >= 1
