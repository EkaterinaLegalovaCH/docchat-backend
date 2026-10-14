"""Document upload, listing, and deletion endpoints."""

import logging
import os
import tempfile
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Request

from app.auth.dependencies import AuthenticatedUser, get_current_user
from app.config import settings
from app.security.rate_limit import delete_limiter, enforce_limit, list_limiter, upload_limiter
from app.db.supabase import (create_document, delete_chunks, delete_document, insert_chunks,
                              list_documents as db_list_documents, remove_storage, update_document,
                              get_client)
from app.models.document import (DeleteResponse, DocumentListItem, DocumentListResponse,
                                 DocumentUploadResponse)
from app.services.pdf_processor import chunk_text, extract_text, validate_pdf
from app.services.provider_errors import raise_safe_provider_error

logger = logging.getLogger(__name__)
router = APIRouter()


def _item(row: dict) -> DocumentListItem:
    return DocumentListItem(id=row["id"], filename=row.get("filename", ""),
                            page_count=row.get("page_count", 0), chunk_count=row.get("chunk_count", 0),
                            status=row.get("status", "processing"), error_message=row.get("error_message"),
                            created_at=row["created_at"])


@router.post("/upload", response_model=DocumentUploadResponse, status_code=201)
async def upload_document(request: Request, file: UploadFile = File(...), user: AuthenticatedUser = Depends(get_current_user)):
    enforce_limit(upload_limiter, user.id)
    request_id = str(uuid.uuid4())
    content = await file.read(settings.max_upload_bytes + 1)
    try:
        validate_pdf(file.filename or "", content, settings.max_upload_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    document_id = str(uuid.uuid4())
    storage_path = f"{user.id}/{document_id}.pdf"
    created_row = None
    stored = False
    try:
        client = get_client()
        client.storage.from_(settings.storage_bucket).upload(
            storage_path, content, {"content-type": "application/pdf", "upsert": "false"}
        )
        stored = True
        created_row = create_document(document_id, file.filename or "document.pdf", storage_path, user.id)
        with tempfile.NamedTemporaryFile(suffix=".pdf") as temporary:
            temporary.write(content)
            temporary.flush()
            page_count, page_texts = extract_text(temporary.name)
        chunks = chunk_text(page_texts)
        chunk_count = insert_chunks(document_id, chunks)
        update_document(document_id, user.id, page_count=page_count, chunk_count=chunk_count, status="ready")
        row = {**created_row, "page_count": page_count, "chunk_count": chunk_count,
               "status": "ready", "created_at": created_row["created_at"]}
        return DocumentUploadResponse(**row)
    except Exception as exc:
        logger.exception("document processing failed request_id=%s document_id=%s", request_id, document_id)
        if created_row is not None:
            try:
                update_document(document_id, user.id, status="failed", error_message="Document processing failed.")
                delete_chunks(document_id)
                remove_storage(storage_path)
            except Exception:
                logger.exception("document cleanup failed request_id=%s document_id=%s", request_id, document_id)
        elif stored:
            try:
                remove_storage(storage_path)
            except Exception:
                logger.exception("storage cleanup failed request_id=%s document_id=%s", request_id, document_id)
        raise_safe_provider_error(
            exc,
            "document processing",
            fallback_detail="Document processing failed. Please try again.",
            fallback_status=500,
        )


@router.get("", response_model=DocumentListResponse)
@router.get("/", response_model=DocumentListResponse, include_in_schema=False)
async def list_documents(user: AuthenticatedUser = Depends(get_current_user)):
    enforce_limit(list_limiter, user.id)
    rows = db_list_documents(user.id)
    return DocumentListResponse(documents=[_item(row) for row in rows], total=len(rows))


@router.delete("/{document_id}", response_model=DeleteResponse)
async def remove_document(document_id: str, user: AuthenticatedUser = Depends(get_current_user)):
    enforce_limit(delete_limiter, user.id)
    if not delete_document(document_id, user.id):
        raise HTTPException(status_code=404, detail="Document not found.")
    return DeleteResponse(deleted=True, document_id=document_id)
