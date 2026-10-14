-- Add ownership without guessing owners for legacy rows.
alter table public.documents add column if not exists user_id uuid;
create index if not exists documents_user_id_idx on public.documents(user_id);

-- Service-role access remains server-side; every application query supplies user_id.
drop function if exists public.match_doc_chunks(vector, float, int, jsonb);
create or replace function public.match_doc_chunks(
  query_embedding vector(1536), match_threshold float, match_count int,
  filter_document_ids jsonb default '[]'::jsonb,
  filter_user_id uuid default null
) returns table (id uuid, document_id uuid, filename text, chunk_index int,
                page_number int, content text, similarity float)
language sql stable as $$
  select dc.id, dc.document_id, d.filename, dc.chunk_index, dc.page_number, dc.content,
    1 - (dc.embedding <=> query_embedding) as similarity
  from public.document_chunks dc join public.documents d on d.id = dc.document_id
  where d.status = 'ready' and d.user_id = filter_user_id
    and 1 - (dc.embedding <=> query_embedding) > match_threshold
    and (filter_document_ids = '[]'::jsonb or dc.document_id in
      (select value::uuid from jsonb_array_elements_text(filter_document_ids)))
  order by dc.embedding <=> query_embedding limit match_count;
$$;

-- Existing rows intentionally remain orphaned (user_id NULL) and are excluded.
