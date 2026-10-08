"""Small, deterministic PDF validation, extraction, and chunking helpers."""

from pathlib import Path
from typing import List, Tuple

import pymupdf


def validate_pdf(filename: str, content: bytes, max_bytes: int) -> None:
    if Path(filename).suffix.lower() != ".pdf":
        raise ValueError("Only PDF files are allowed.")
    if len(content) > max_bytes:
        raise ValueError("The PDF exceeds the 10 MB upload limit.")
    if not content.startswith(b"%PDF-"):
        raise ValueError("The uploaded file is not a valid PDF.")


def extract_text(path: str) -> Tuple[int, List[str]]:
    with pymupdf.open(path) as doc:
        return doc.page_count, [page.get_text().strip() for page in doc]


def chunk_text(page_texts: List[str], chunk_size: int = 1000, overlap: int = 200) -> List[dict]:
    """Split each page into overlapping chunks, retaining page provenance."""
    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be non-negative and smaller than chunk_size")
    chunks: list[dict] = []
    step = chunk_size - overlap
    for page_number, page_text in enumerate(page_texts, start=1):
        if not page_text:
            continue
        for start in range(0, len(page_text), step):
            chunks.append({
                "text": page_text[start:start + chunk_size],
                "page_number": page_number,
                "chunk_index": len(chunks),
            })
            if start + chunk_size >= len(page_text):
                break
    return chunks
