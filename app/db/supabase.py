"""
Supabase / Postgres vector store interface.

Handles:
  - Creating the chunks table with pgvector extension
  - Inserting document chunks with embeddings
  - Searching for similar chunks via cosine similarity
  - Deleting chunks when a document is removed
"""

import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from supabase import create_client, Client
from app.config import settings
from app.services.embeddings import embed_texts


class SupabaseChunk:
    """A single row from the doc_chunks table."""
    def __init__(
        self,
        id: str,
        document_id: str,
        document_name: str,
        chunk_index: int,
        page_number: int,
        text: str,
        embedding: Optional[List[float]] = None,
        created_at: Optional[str] = None,
    ):
        self.id = id
        self.document_id = document_id
        self.document_name = document_name
        self.chunk_index = chunk_index
        self.page_number = page_number
        self.text = text
        self.embedding = embedding
        self.created_at = created_at


def _get_client() -> Client:
    """Return an authenticated Supabase client."""
    if not settings.supabase_url or not settings.supabase_key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set.")
    return create_client(settings.supabase_url, settings.supabase_key)


def ensure_table() -> None:
    """
    Ensure the doc_chunks table exists with the pgvector extension.
    Run this once at startup.
    
    NOTE: Table creation via the Supabase REST API is limited.
    For production, run the SQL from the README manually in the
    Supabase SQL editor. This method tries the REST API first.
    """
    # The actual table creation requires the Supabase dashboard SQL editor.
    # Here we just do a quick test query to see if the table is accessible.
    try:
        client = _get_client()
        client.table(settings.supabase_chunks_table).select("id").limit(1).execute()
    except Exception:
        # Table may not exist yet — that's OK, the README explains setup.
        pass


def insert_chunks(
    document_id: str,
    document_name: str,
    chunks: List[dict],
) -> int:
    """
    Embed chunk texts and insert them into the Supabase table.

    Parameters
    ----------
    document_id : str
        A unique ID for the document (you generate it).
    document_name : str
        The original filename.
    chunks : list of dict
        Each dict has: text, page_number, chunk_index

    Returns
    -------
    int — the number of chunks inserted.
    """
    client = _get_client()
    texts = [c["text"] for c in chunks]
    embeddings = embed_texts(texts)

    rows = []
    now = datetime.now(timezone.utc).isoformat()
    for chunk, embedding in zip(chunks, embeddings):
        rows.append({
            "id": str(uuid.uuid4()),
            "document_id": document_id,
            "document_name": document_name,
            "chunk_index": chunk["chunk_index"],
            "page_number": chunk["page_number"],
            "text": chunk["text"],
            "embedding": json.dumps(embedding),  # Supabase REST expects JSON
            "created_at": now,
        })

    result = client.table(settings.supabase_chunks_table).insert(rows).execute()
    return len(result.data)


def search_chunks(
    query_vector: List[float],
    top_k: int = 5,
    document_ids: Optional[List[str]] = None,
) -> List[SupabaseChunk]:
    """
    Search for the top-K most similar chunks using cosine similarity.

    The actual vector search uses a Postgres function defined in Supabase:

        CREATE OR REPLACE FUNCTION match_doc_chunks(
            query_embedding vector(1536),
            match_threshold float,
            match_count int,
            filter_document_ids jsonb DEFAULT '[]'
        )

    If the function doesn't exist yet, fall back to a simpler query
    (less efficient but works for small datasets).
    """
    client = _get_client()

    try:
        # Preferred: use the RPC function
        params = {
            "query_embedding": query_vector,
            "match_threshold": 0.5,
            "match_count": top_k,
            "filter_document_ids": json.dumps(document_ids or []),
        }
        result = client.rpc("match_doc_chunks", params).execute()
        rows = result.data
    except Exception:
        # Fallback: fetch all chunks and filter in Python.
        # This is fine for demos; replace with the RPC for production.
        query = client.table(settings.supabase_chunks_table).select("*")
        if document_ids:
            query = query.in_("document_id", document_ids)
        result = query.execute()
        rows = sorted(
            result.data or [],
            key=lambda r: _cosine_sim(
                json.loads(r.get("embedding", "[]")), query_vector
            ),
            reverse=True,
        )[:top_k]

    return [_row_to_chunk(r) for r in rows]


def delete_document_chunks(document_id: str) -> int:
    """Delete all chunks belonging to a document. Returns count of deleted rows."""
    client = _get_client()
    result = (
        client.table(settings.supabase_chunks_table)
        .delete()
        .eq("document_id", document_id)
        .execute()
    )
    return len(result.data)


def get_chunk_count(document_id: str) -> int:
    """Return how many chunks exist for a given document."""
    client = _get_client()
    result = (
        client.table(settings.supabase_chunks_table)
        .select("id", count="exact")
        .eq("document_id", document_id)
        .execute()
    )
    return result.count or 0


def get_document_list() -> List[dict]:
    """
    Return a deduplicated list of documents that have chunks in the DB.
    Each entry: {id, document_name, chunk_count, page_count, created_at}
    """
    client = _get_client()
    result = client.table(settings.supabase_chunks_table).select(
        "document_id, document_name, page_number, created_at"
    ).execute()

    docs: dict[str, dict] = {}
    for row in result.data or []:
        did = row["document_id"]
        if did not in docs:
            docs[did] = {
                "id": did,
                "document_name": row.get("document_name", "Unknown"),
                "chunk_count": 0,
                "page_count": 0,
                "created_at": row.get("created_at", ""),
            }
        docs[did]["chunk_count"] += 1
        # Rough page estimate: track unique page numbers
        # (In production, store page_count in a separate documents table)
        if row.get("page_number"):
            docs[did]["page_count"] = max(docs[did]["page_count"], row["page_number"])

    return list(docs.values())


# ── Helpers ─────────────────────────────────────────────────────────


def _row_to_chunk(row: dict) -> SupabaseChunk:
    return SupabaseChunk(
        id=row.get("id", ""),
        document_id=row.get("document_id", ""),
        document_name=row.get("document_name", ""),
        chunk_index=row.get("chunk_index", 0),
        page_number=row.get("page_number", 0),
        text=row.get("text", ""),
        embedding=json.loads(row.get("embedding", "[]")) if row.get("embedding") else None,
        created_at=row.get("created_at"),
    )


def _cosine_sim(a: List[float], b: List[float]) -> float:
    """Cosine similarity between two vectors."""
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)