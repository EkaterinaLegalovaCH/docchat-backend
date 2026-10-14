from pathlib import Path


def test_auth_migration_adds_nullable_ownership_and_rpc_filter():
    migration = Path("supabase/migrations/003_auth_ownership.sql").read_text()
    assert "add column if not exists user_id uuid" in migration
    assert "documents_user_id_idx" in migration
    assert "d.user_id = filter_user_id" in migration


def test_initial_schema_uses_1536_dimensions_for_column_and_rpc():
    schema = Path("supabase/migrations/001_initial_schema.sql").read_text()

    assert "embedding vector(1536)" in schema
    assert "query_embedding vector(1536)" in schema
    assert "vector(384)" not in schema
