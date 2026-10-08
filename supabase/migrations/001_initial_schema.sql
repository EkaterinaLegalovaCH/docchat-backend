-- DocChat initial schema. Safe to run more than once.
create extension if not exists vector;

create table if not exists public.documents (
  id uuid primary key,
  filename text not null,
  title text not null,
  storage_path text not null unique,
  page_count integer not null default 0,
  chunk_count integer not null default 0,
  status text not null default 'processing' check (status in ('processing', 'ready', 'failed')),
  error_message text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.document_chunks (
  id uuid primary key,
  document_id uuid not null references public.documents(id) on delete cascade,
  chunk_index integer not null,
  content text not null,
  page_number integer not null,
  embedding vector(1536) not null,
  created_at timestamptz not null default now(),
  unique (document_id, chunk_index)
);

create index if not exists document_chunks_document_id_idx on public.document_chunks(document_id);
create index if not exists document_chunks_embedding_idx on public.document_chunks
  using ivfflat (embedding vector_cosine_ops) with (lists = 100);
create index if not exists documents_created_at_idx on public.documents(created_at desc);

create or replace function public.set_updated_at() returns trigger
language plpgsql as $$ begin new.updated_at = now(); return new; end; $$;
drop trigger if exists documents_set_updated_at on public.documents;
create trigger documents_set_updated_at before update on public.documents
for each row execute function public.set_updated_at();

create or replace function public.match_doc_chunks(
  query_embedding vector(384), match_threshold float, match_count int,
  filter_document_ids jsonb default '[]'::jsonb
) returns table (id uuid, document_id uuid, filename text, chunk_index int,
  page_number int, content text, similarity float)
language sql stable as $$
  select dc.id, dc.document_id, d.filename, dc.chunk_index, dc.page_number, dc.content,
    1 - (dc.embedding <=> query_embedding) as similarity
  from public.document_chunks dc join public.documents d on d.id = dc.document_id
  where d.status = 'ready'
    and 1 - (dc.embedding <=> query_embedding) > match_threshold
    and (filter_document_ids = '[]'::jsonb or dc.document_id in
      (select value::uuid from jsonb_array_elements_text(filter_document_ids)))
  order by dc.embedding <=> query_embedding limit match_count;
$$;

-- Portfolio demo: the backend uses the service role, while the browser has no DB access.
alter table public.documents enable row level security;
alter table public.document_chunks enable row level security;
drop policy if exists "backend service role documents" on public.documents;
drop policy if exists "backend service role chunks" on public.document_chunks;
create policy "backend service role documents" on public.documents for all to service_role using (true) with check (true);
create policy "backend service role chunks" on public.document_chunks for all to service_role using (true) with check (true);

-- Storage bucket setup is not portable through SQL in all Supabase versions.
-- Create a private bucket named 'documents' in Storage, or set STORAGE_BUCKET to your bucket name.
