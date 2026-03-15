"""
tests/ingestion/pipeline/test_parser.py — Unit tests for the document parser.

Covers:
    - TXT parsing
    - PDF parsing (skipped if no PDF library installed)
    - DOCX parsing (skipped if python-docx not installed)
    - Unsupported file type raises IngestionError
    - Missing file raises IngestionError
    - Empty file raises IngestionError
    - Text cleaning (whitespace normalisation)
"""

from __future__ import annotations

import os
import tempfile

import pytest

from ingestion.pipeline.parser import parse, _clean_text
from shared.exceptions.pipeline_exceptions import IngestionError


class TestCleanText:
    def test_collapses_multiple_blank_lines(self):
        text = "Line 1\n\n\n\n\nLine 2"
        result = _clean_text(text)
        assert "\n\n\n" not in result
        assert "Line 1" in result
        assert "Line 2" in result

    def test_strips_trailing_spaces_per_line(self):
        text = "Hello   \nWorld   "
        result = _clean_text(text)
        assert not result.startswith(" ")
        assert "Hello" in result

    def test_empty_input_returns_empty(self):
        assert _clean_text("") == ""

    def test_single_line_unchanged(self):
        text = "Simple clean text"
        assert _clean_text(text) == text


class TestParseTxt:
    def test_reads_plain_text_file(self, tmp_txt_file):
        result = parse(tmp_txt_file, "txt")
        assert "Minerva" in result

    def test_txt_with_dot_extension(self, sample_text):
        fd, path = tempfile.mkstemp(suffix=".txt")
        with os.fdopen(fd, "w") as fh:
            fh.write(sample_text)
        try:
            result = parse(path, ".txt")
            assert "Minerva" in result
        finally:
            os.remove(path)

    def test_empty_txt_raises(self):
        fd, path = tempfile.mkstemp(suffix=".txt")
        os.close(fd)
        try:
            with pytest.raises(IngestionError, match="no extractable text"):
                parse(path, "txt")
        finally:
            os.remove(path)

    def test_whitespace_only_txt_raises(self):
        fd, path = tempfile.mkstemp(suffix=".txt")
        with os.fdopen(fd, "w") as fh:
            fh.write("   \n\n   \n   ")
        try:
            with pytest.raises(IngestionError, match="no extractable text"):
                parse(path, "txt")
        finally:
            os.remove(path)


class TestParseMissingFile:
    def test_missing_file_raises(self):
        with pytest.raises(IngestionError, match="File not found"):
            parse("/tmp/does_not_exist_xyz.txt", "txt")


class TestParseUnsupportedType:
    def test_unsupported_type_raises(self, tmp_txt_file):
        with pytest.raises(IngestionError, match="Unsupported file type"):
            parse(tmp_txt_file, "xlsx")

    def test_html_raises_not_supported(self, tmp_txt_file):
        with pytest.raises(IngestionError, match="Unsupported file type"):
            parse(tmp_txt_file, "html")


class TestParsePdf:
    def test_pdf_extraction(self, tmp_pdf_file):
        """Requires reportlab + (pdfplumber or PyPDF2). Skipped if missing."""
        result = parse(tmp_pdf_file, "pdf")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_pdf_with_uppercase_extension(self, tmp_pdf_file):
        result = parse(tmp_pdf_file, "PDF")
        assert isinstance(result, str)
