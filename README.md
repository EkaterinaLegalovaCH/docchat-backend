# DocChat — RAG Backend

A FastAPI application that turns uploaded PDFs into a searchable knowledge base.
Ask questions in natural language; get answers backed by source citations.

## Architecture

```
Upload PDF ──► Extract text ──► Chunk ──► Embed ──► Store in Supabase/pgvector
                                                            │
Ask question ──────────────────────────────────────────────► Search top-K chunks
                                                            │
                                                    Build prompt + context
                                                            │
                                                    OpenAI answer + citations
```

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Fill in your OPENAI_API_KEY, SUPABASE_URL, SUPABASE_KEY
uvicorn app.main:app --reload
```

## Supabase Setup

Run this SQL in the Supabase SQL Editor to create the vector store:

```sql
-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Create the chunks table
CREATE TABLE doc_chunks (
    id UUID PRIMARY KEY,
    document_id TEXT NOT NULL,
    document_name TEXT NOT NULL,
    chunk_index INT NOT NULL,
    page_number INT NOT NULL,
    text TEXT NOT NULL,
    embedding VECTOR(1536),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create the match function for vector search
CREATE OR REPLACE FUNCTION match_doc_chunks(
    query_embedding VECTOR(1536),
    match_threshold FLOAT,
    match_count INT,
    filter_document_ids JSONB DEFAULT '[]'::jsonb
)
RETURNS TABLE(
    id UUID,
    document_id TEXT,
    document_name TEXT,
    chunk_index INT,
    page_number INT,
    text TEXT,
    embedding VECTOR(1536),
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        dc.id,
        dc.document_id,
        dc.document_name,
        dc.chunk_index,
        dc.page_number,
        dc.text,
        dc.embedding::VECTOR(1536),
        1 - (dc.embedding <=> query_embedding) AS similarity
    FROM doc_chunks dc
    WHERE
        1 - (dc.embedding <=> query_embedding) > match_threshold
        AND (
            filter_document_ids = '[]'::jsonb
            OR dc.document_id IN (
                SELECT value::TEXT FROM jsonb_array_elements_text(filter_document_ids)
            )
        )
    ORDER BY similarity DESC
    LIMIT match_count;
END;
$$;

-- Create an index for faster search (IVFFlat with 100 centroids)
CREATE INDEX idx_doc_chunks_embedding ON doc_chunks
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

## API Endpoints

| Method | Path                   | Description                |
|--------|------------------------|----------------------------|
| GET    | /api/health            | Health check               |
| POST   | /api/documents/upload  | Upload a PDF               |
| GET    | /api/documents/        | List all documents         |
| DELETE | /api/documents/{id}    | Delete a document          |
| POST   | /api/chat/ask          | Ask a question             |

## Example

```bash
# Upload a PDF
curl -X POST http://localhost:8000/api/documents/upload \
  -F "file=@report.pdf"

# Ask a question
curl -X POST http://localhost:8000/api/chat/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the key findings?"}'
```