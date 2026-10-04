"""
DocChat configuration — loaded from environment variables.

All settings are documented here so you know exactly what to set.
When deploying, set these in your environment or .env file.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # ── OpenAI ──────────────────────────────────────────────────────────
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"           # for Q&A answers
    embedding_model: str = "text-embedding-3-small"  # for vector embeddings

    # ── Supabase (Postgres + pgvector) ──────────────────────────────────
    supabase_url: str = ""
    supabase_key: str = ""
    # The table that stores document chunks + embeddings
    supabase_chunks_table: str = "doc_chunks"

    # ── Storage ─────────────────────────────────────────────────────────
    upload_dir: str = "./uploads"

    # ── Server ──────────────────────────────────────────────────────────
    app_name: str = "DocChat"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()