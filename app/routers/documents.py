"""
Documents router — upload, list, and delete PDFs.
"""

import os
import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, UploadFile, File, HTTPException
from app.config import settings
from app.models.document import (
    DocumentUploadResponse,
    DocumentListItem,
    DocumentListResponse,
    DeleteResponse,
)
from app.services.pdf_processor import extract_text, chunk_text
from app.db.supabase import insert_chunks, delete_document_chunks, get_chunk_count, get_document_list

router = APIRouter()

# Allowed file extensions
ALLOWED_EXTENSIONS = {".pdf"}


@router.post("/upload", response_model=DocumentUploadResponse, status_code=201)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a PDF file. The file is:
      1. Saved to the upload directory
      2. Text is extracted and split into overlapping chunks
      3. Each chunk is embedded and stored in Supabase

    Returns document metadata including chunk count.
    """
    # ── Validate file type ──────────────────────────────────────────────
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Only PDFs are allowed.",
        )

    # ── Save to disk ────────────────────────────────────────────────────
    document_id = str(uuid.uuid4())
    safe_name = f"{document_id}{ext}"
    file_path = os.path.join(settings.upload_dir, safe_name)

    os.makedirs(settings.upload_dir, exist_ok=True)
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    try:
        # ── Extract & chunk ─────────────────────────────────────────────
        page_count, page_texts = extract_text(file_path)
        chunks = chunk_text(page_texts)

        # ── Embed & store ────────────────────────────────────────────────
        chunk_count = insert_chunks(
            document_id=document_id,
            document_name=file.filename or "unnamed.pdf",
            chunks=chunks,
        )

        return DocumentUploadResponse(
            id=document_id,
            filename=file.filename or "unnamed.pdf",
            page_count=page_count,
            chunk_count=chunk_count,
            created_at=datetime.now(timezone.utc),
        )

    except Exception as exc:
        # Clean up the saved file on failure
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/", response_model=DocumentListResponse)
async def list_documents():
    """
    Return all documents that have been uploaded and indexed.
    Data comes from the vector store (chunks table).
    """
    docs = get_document_list()
    items = [
        DocumentListItem(
            id=d["id"],
            filename=d["document_name"],
            page_count=d["page_count"],
            chunk_count=d["chunk_count"],
            created_at=datetime.fromisoformat(d["created_at"]) if d.get("created_at") else datetime.now(timezone.utc),
        )
        for d in docs
    ]
    return DocumentListResponse(documents=items, total=len(items))


@router.delete("/{document_id}", response_model=DeleteResponse)
async def delete_document(document_id: str):
    """
    Delete a document and all of its chunks from the vector store.
    Also removes the uploaded file from disk if it exists.
    """
    # Delete from vector store
    deleted_count = delete_document_chunks(document_id)

    # Delete from disk (try all possible extensions)
    for ext in ALLOWED_EXTENSIONS:
        file_path = os.path.join(settings.upload_dir, f"{document_id}{ext}")
        if os.path.exists(file_path):
            os.remove(file_path)

    if deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail=f"No document found with id '{document_id}'.",
        )

    return DeleteResponse(deleted=True, document_id=document_id)