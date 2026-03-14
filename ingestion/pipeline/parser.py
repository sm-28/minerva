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
