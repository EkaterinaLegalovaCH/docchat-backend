# DocChat backend

A small FastAPI RAG service: PDFs are validated, stored in Supabase Storage, chunked with PyMuPDF, embedded with OpenAI `text-embedding-3-small`, and searched through a Supabase pgvector RPC. Answers use OpenAI `gpt-4o-mini`.

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in values locally; never paste secrets into chat
chmod 600 .env
chmod +x run.sh
./run.sh --reload
curl http://localhost:8000/api/health
curl http://localhost:8000/api/ready
```

`/api/health` is liveness only. `/api/ready` reports missing settings or checks Supabase. For a new database, run `supabase/migrations/001_initial_schema.sql`. If the existing Supabase project was created from the earlier 384-dimensional migration, run `supabase/migrations/002_use_openai_embeddings_1536.sql` in the SQL Editor. It removes incompatible chunks, preserves source documents, and marks them for reprocessing. Re-upload the PDFs afterward. Create a **private** Storage bucket named `documents` (or change `STORAGE_BUCKET`).

## Environment

| Variable | Purpose |
|---|---|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_KEY` | backend-only service-role key; never expose it in Vite |
| `OPENAI_API_KEY` | backend-only OpenAI API key |
| `OPENAI_MODEL` | answer model, default `gpt-4o-mini` |
| `EMBEDDING_MODEL` | embedding model, default `text-embedding-3-small` |
| `CORS_ORIGINS` | comma-separated browser origins |
| `STORAGE_BUCKET` | private PDF bucket, default `documents` |
| `MAX_UPLOAD_SIZE_MB` | upload limit, default 10 |

The embedding model returns 1536-dimensional vectors, matching the `vector(1536)` database column and RPC. OpenAI API usage may incur account charges; hosting and model API costs are separate. Local embeddings and xAI/Grok were considered and rejected for this implementation.

The unauthenticated portfolio demo is not production multi-user software. The service-role credential must remain only on the backend. Add authentication and rate limiting before exposing it to untrusted users.

## API and smoke tests

```bash
curl -F 'file=@sample.pdf' http://localhost:8000/api/documents/upload
curl http://localhost:8000/api/documents
curl -X DELETE http://localhost:8000/api/documents/<id>
PYTHONPATH=. .venv/bin/pytest -q
.venv/bin/python -m compileall -q app
# Optional external smoke test; requires local .env credentials and a real PDF.
./scripts/smoke_test.sh path/to/sample.pdf
```

Deployment can use Render for the backend and Vercel for the frontend. Configure the backend environment variables in the hosting dashboard and set Vercel's `VITE_API_URL` to the backend URL. Do not deploy until the real upload → retrieval → answer → citations → deletion smoke test passes.
