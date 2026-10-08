-- Move an existing DocChat database to OpenAI text-embedding-3-small (1536 dimensions).
-- Existing chunks are incompatible and are removed; source documents remain available
-- for reprocessing by uploading them again.
create extension if not exists vector;

alter table public.document_chunks add column if not exists embedding_1536 vector(1536);
truncate table public.document_chunks;
alter table public.document_chunks drop column if exists embedding;
alter table public.document_chunks rename column embedding_1536 to embedding;
alter table public.document_chunks alter column embedding set not null;

create index if not exists document_chunks_embedding_idx on public.document_chunks
  using ivfflat (embedding vector_cosine_ops) with (lists = 100);

drop function if exists public.match_doc_chunks(vector, float, int, jsonb);
create or replace function public.match_doc_chunks(
  query_embedding vector(1536), match_threshold float, match_count int,
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

update public.documents set status = 'processing', chunk_count = 0, updated_at = now();
