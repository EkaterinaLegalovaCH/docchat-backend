"""
Pydantic models for chat / Q&A requests and responses.
"""

from pydantic import BaseModel, Field
from typing import Optional

from app.config import settings


class ChatRequest(BaseModel):
    """Incoming question from the user."""
    question: str = Field(min_length=1, max_length=settings.max_question_length)
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