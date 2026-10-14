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

`/api/health` is liveness only. `/api/ready` reports missing settings or checks Supabase without exposing provider errors. For a new database, run `supabase/migrations/001_initial_schema.sql`; existing projects should also run `003_auth_ownership.sql` after the embedding migration. Migration 003 adds nullable `documents.user_id`: old rows remain orphaned and are never shown to authenticated users, while new uploads require an owner. Create a **private** Storage bucket named `documents` (or change `STORAGE_BUCKET`).

All document and chat endpoints require `Authorization: Bearer <Supabase access token>`. The server validates tokens with Supabase Auth and uses the service-role client only on the backend. Storage paths are `{user_id}/{document_id}.pdf`; database list/delete/retrieval queries apply the same user filter, including inside the vector RPC.

The single-instance in-memory fixed-window limits are 20 chat requests/minute/user and 5 uploads/minute/user. `MAX_UPLOAD_SIZE_MB` remains the upload cap and `MAX_QUESTION_LENGTH` defaults to 2000 characters. These limits are intentionally conservative for one Render instance and should be replaced with shared infrastructure before horizontal scaling.

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
| `MAX_QUESTION_LENGTH` | question limit, default 2000 characters |

The embedding model returns 1536-dimensional vectors, matching the `vector(1536)` database column and RPC. OpenAI API usage may incur account charges; hosting and model API costs are separate. Local embeddings and xAI/Grok were considered and rejected for this implementation.

Authentication uses Supabase email/password sessions. Protected routes require a Bearer token and scope documents to the authenticated user. New files use `{user_id}/{document_id}.pdf` storage paths. Existing rows with `user_id IS NULL` are orphaned legacy records and are excluded after applying `003_auth_ownership.sql`.

The backend uses conservative in-memory limits for a single Render instance: 5 uploads/minute/user, 20 questions/minute/user, 30 document lists/minute/user, 10 deletes/minute/user, and 2,000 characters per question. These limits are not a substitute for a distributed rate limiter in a multi-instance deployment.

The service-role credential must remain only on the backend. Configure the frontend with the public Supabase URL and anon key only. Before exposing the app to broad public use, consider stronger distributed rate limiting, abuse monitoring, and additional account controls.

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
