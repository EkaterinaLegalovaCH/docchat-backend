"""
PDF text extraction using PyMuPDF (fitz).

Given a file path, extracts:
  - page_count
  - per-page text content
  - a list of text chunks suitable for embedding
"""

import fitz  # PyMuPDF
from typing import List, Tuple


def extract_text(path: str) -> Tuple[int, List[str]]:
    """
    Extract text from a PDF file.

    Returns (page_count, list_of_page_texts).
    Each element of page_texts is the full text of one page.
    """
    doc = fitz.open(path)
    page_count = doc.page_count
    page_texts: list[str] = []

    for page_num in range(page_count):
        page = doc.load_page(page_num)
        text = page.get_text().strip()
        page_texts.append(text)

    doc.close()
    return page_count, page_texts


def chunk_text(
    page_texts: List[str],
    chunk_size: int = 1000,
    overlap: int = 200,
) -> List[dict]:
    """
    Split full-page texts into overlapping chunks suitable for embedding.

    Each chunk dict contains:
      - text: the chunk text
      - page_number: which page it came from
      - chunk_index: the chunk's position within the document

    The overlap ensures that a question spanning a chunk boundary
    still has a chance to match one of the overlapping chunks.
    """
    chunks: list[dict] = []
    chunk_index = 0

    for page_number, page_text in enumerate(page_texts, start=1):
        if not page_text:
            continue

        start = 0
        while start < len(page_text):
            end = start + chunk_size
            chunk_text_content = page_text[start:end]

            chunks.append({
                "text": chunk_text_content,
                "page_number": page_number,
                "chunk_index": chunk_index,
            })

            chunk_index += 1
            # Move forward by (chunk_size - overlap) so consecutive chunks overlap
            step = chunk_size - overlap
            if step <= 0:
                step = chunk_size  # safety: never infinite loop
            start += step

    return chunks