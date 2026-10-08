"""Pydantic models for document API responses."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
    id: str
    filename: str
    page_count: int
    chunk_count: int
    status: str
    error_message: Optional[str] = None
    created_at: datetime


class DocumentListItem(BaseModel):
    id: str
    filename: str
    page_count: int
    chunk_count: int
    status: str
    error_message: Optional[str] = None
    created_at: datetime


class DocumentListResponse(BaseModel):
    documents: list[DocumentListItem]
    total: int


class DeleteResponse(BaseModel):
    deleted: bool
    document_id: str
