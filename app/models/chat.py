"""
Pydantic models for chat / Q&A requests and responses.
"""

from pydantic import BaseModel
from typing import Optional


class ChatRequest(BaseModel):
    """Incoming question from the user."""
    question: str
    document_ids: Optional[list[str]] = None  # filter to these docs; None = all


class Citation(BaseModel):
    """A single source citation backing an answer."""
    document_id: str
    document_name: str
    page_number: Optional[int] = None
    chunk_index: int
    text_snippet: str  # the relevant excerpt


class ChatResponse(BaseModel):
    """The answer and its supporting citations."""
    answer: str
    citations: list[Citation]
    model: str