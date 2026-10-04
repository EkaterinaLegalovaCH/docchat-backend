"""
Pydantic models for document-related API requests and responses.
"""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class DocumentUploadResponse(BaseModel):
    """Returned after a successful PDF upload."""
    id: str
    filename: str
    page_count: int
    chunk_count: int
    created_at: datetime


class DocumentListItem(BaseModel):
    """A summary of one uploaded document, used in listing."""
    id: str
    filename: str
    page_count: int
    chunk_count: int
    created_at: datetime


class DocumentListResponse(BaseModel):
    """Wrapper for the document list endpoint."""
    documents: list[DocumentListItem]
    total: int


class DeleteResponse(BaseModel):
    """Confirmation after deleting a document."""
    deleted: bool
    document_id: str