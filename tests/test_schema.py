from pathlib import Path


def test_initial_schema_uses_1536_dimensions_for_column_and_rpc():
    schema = Path("supabase/migrations/001_initial_schema.sql").read_text()

    assert "embedding vector(1536)" in schema
    assert "query_embedding vector(1536)" in schema
    assert "vector(384)" not in schema
