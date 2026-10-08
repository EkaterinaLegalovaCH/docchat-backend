"""Typed application settings loaded from environment variables."""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "DocChat"
    supabase_url: str = ""
    supabase_key: str = ""  # server-side service key; never expose to the frontend
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    storage_bucket: str = "documents"
    max_upload_size_mb: int = 10

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        enable_decoding=False,
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("embedding_dimension")
    @classmethod
    def validate_embedding_dimension(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("embedding_dimension must be positive")
        return value

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def chat_api_key(self) -> str:
        return self.openai_api_key

    @property
    def chat_model(self) -> str:
        return self.openai_model


settings = Settings()
