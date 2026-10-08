"""Supabase database and Storage access. All calls use the canonical schema."""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from supabase import Client, create_client

from app.config import settings
from app.services.embeddings import embed_texts

logger = logging.getLogger(__name__)


class SupabaseChunk:
    def __init__(self, id: str, document_id: str, document_name: str, chunk_index: int,
                 page_number: int, text: str, created_at: Optional[str] = None):
        self.id, self.document_id, self.document_name = id, document_id, document_name
        self.chunk_index, self.page_number, self.text = chunk_index, page_number, text
        self.created_at = created_at


def get_client() -> Client:
    if not settings.supabase_url or not settings.supabase_key:
        raise RuntimeError("Supabase is not configured.")
    return create_client(settings.supabase_url, settings.supabase_key)


def check_connection() -> None:
    get_client().table("documents").select("id").limit(1).execute()


def create_document(document_id: str, filename: str, storage_path: str) -> dict:
    row = {"id": document_id, "filename": filename, "title": filename,
           "storage_path": storage_path, "status": "processing"}
    result = get_client().table("documents").insert(row).execute()
    return result.data[0]


def update_document(document_id: str, **values: object) -> None:
    get_client().table("documents").update(values).eq("id", document_id).execute()


def list_documents() -> list[dict]:
    result = get_client().table("documents").select(
        "id,filename,title,page_count,chunk_count,status,error_message,created_at"
    ).order("created_at", desc=True).execute()
    return result.data or []


def get_document(document_id: str) -> Optional[dict]:
    result = get_client().table("documents").select("*").eq("id", document_id).limit(1).execute()
    return result.data[0] if result.data else None


def insert_chunks(document_id: str, chunks: list[dict]) -> int:
    if not chunks:
        return 0
    embeddings = embed_texts([chunk["text"] for chunk in chunks])
    rows = [{"id": str(uuid.uuid4()), "document_id": document_id,
             "chunk_index": chunk["chunk_index"], "content": chunk["text"],
             "page_number": chunk["page_number"], "embedding": embedding}
            for chunk, embedding in zip(chunks, embeddings)]
    result = get_client().table("document_chunks").insert(rows).execute()
    return len(result.data or [])


def search_chunks(query_vector: list[float], top_k: int = 5,
                  document_ids: Optional[list[str]] = None) -> list[SupabaseChunk]:
    params = {"query_embedding": query_vector, "match_threshold": 0.5,
              "match_count": top_k, "filter_document_ids": document_ids or []}
    rows = get_client().rpc("match_doc_chunks", params).execute().data or []
    return [_row_to_chunk(row) for row in rows]


def delete_document(document_id: str) -> bool:
    client = get_client()
    document = get_document(document_id)
    if not document:
        return False
    storage_path = document.get("storage_path")
    if storage_path:
        client.storage.from_(settings.storage_bucket).remove([storage_path])
    client.table("documents").delete().eq("id", document_id).execute()
    return True


def delete_chunks(document_id: str) -> None:
    get_client().table("document_chunks").delete().eq("document_id", document_id).execute()


def remove_storage(path: str) -> None:
    get_client().storage.from_(settings.storage_bucket).remove([path])


def _row_to_chunk(row: dict) -> SupabaseChunk:
    return SupabaseChunk(id=row.get("id", ""), document_id=row.get("document_id", ""),
                         document_name=row.get("filename", row.get("document_name", "")),
                         chunk_index=row.get("chunk_index", 0), page_number=row.get("page_number", 0),
                         text=row.get("content", row.get("text", "")), created_at=row.get("created_at"))
