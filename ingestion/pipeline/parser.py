"""
ingestion/pipeline/parser.py — Document text extraction.

Purpose:
    Extracts raw text from uploaded documents. Supports multiple formats.

Supported Formats:
    - PDF (via pdfplumber or PyPDF)
    - Future: DOCX, TXT, HTML

Methods:
    parse(file_path: str, file_type: str) → str

Notes:
    - Text is cleaned to remove excessive whitespace, headers/footers.
    - Returns raw text string ready for chunking.
"""

import os
import re

from shared.exceptions.pipeline_exceptions import IngestionError
from shared.utils.logging import get_logger

logger = get_logger("ingestion.pipeline.parser")


def parse(file_path: str, file_type: str) -> str:
    """
    Extract and clean raw text from a document file.

    Args:
        file_path: Absolute path to the downloaded document on disk.
        file_type: MIME-friendly type string, e.g. 'pdf', 'txt', 'docx'.

    Returns:
        Cleaned text as a single string.

    Raises:
        IngestionError: If the file cannot be read or the type is unsupported.
    """
    file_type = file_type.lower().strip(".")

    if not os.path.exists(file_path):
        raise IngestionError("parse", f"File not found: {file_path}")

    logger.info(f"Parsing document: {file_path} (type={file_type})")

    if file_type == "pdf":
        text = _parse_pdf(file_path)
    elif file_type == "txt":
        text = _parse_txt(file_path)
    elif file_type == "docx":
        text = _parse_docx(file_path)
    else:
        raise IngestionError("parse", f"Unsupported file type: '{file_type}'")

    text = _clean_text(text)

    if not text.strip():
        raise IngestionError("parse", "Parsed document produced no extractable text.")

    logger.info(f"Parsed {len(text)} characters from {os.path.basename(file_path)}")
    return text


# ── Format handlers ───────────────────────────────────────────────────────────

def _parse_pdf(file_path: str) -> str:
    """Extract text from a PDF using pdfplumber (preferred) or PyPDF2 fallback."""
    try:
        import pdfplumber  # type: ignore

        pages: list[str] = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    pages.append(page_text)
        return "\n".join(pages)

    except ImportError:
        pass  # fall through to PyPDF2

    try:
        from PyPDF2 import PdfReader  # type: ignore

        reader = PdfReader(file_path)
        pages = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                pages.append(page_text)
        return "\n".join(pages)

    except ImportError as exc:
        raise IngestionError(
            "parse",
            "No PDF library available. Install 'pdfplumber' or 'PyPDF2'.",
        ) from exc


def _parse_txt(file_path: str) -> str:
    """Read a plain-text file."""
    with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def _parse_docx(file_path: str) -> str:
    """Extract text from a .docx file using python-docx."""
    try:
        from docx import Document  # type: ignore

        doc = Document(file_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)

    except ImportError as exc:
        raise IngestionError(
            "parse",
            "python-docx is not installed. Run: pip install python-docx",
        ) from exc


# ── Text cleaning ─────────────────────────────────────────────────────────────

def _clean_text(text: str) -> str:
    """
    Normalise text extracted from a document.

    Removes:
    - Excessive blank lines (>2 consecutive)
    - Non-printing control characters (except newlines/tabs)
    - Leading/trailing whitespace per line
    """
    # Strip control characters except newline and tab
    text = re.sub(r"[^\S\n\t]+", " ", text)        # collapse horizontal whitespace
    text = re.sub(r" +\n", "\n", text)              # trailing spaces before newline
    text = re.sub(r"\n{3,}", "\n\n", text)          # max two consecutive blank lines
    text = text.strip()
    return text
