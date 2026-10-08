"""OpenAI embeddings used by both document indexing and question search."""

from openai import OpenAI

from app.config import settings


def readiness() -> dict[str, object]:
    """Report embedding configuration without making a paid API request."""
    return {
        "available": bool(settings.openai_api_key),
        "model": settings.embedding_model,
        "dimension": settings.embedding_dimension,
    }


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed text strings and validate every vector before database insertion."""
    if not texts:
        return []
    if not settings.openai_api_key:
        raise RuntimeError("OpenAI API key is not configured.")

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.embeddings.create(model=settings.embedding_model, input=texts)
    vectors = [item.embedding for item in response.data]
    if len(vectors) != len(texts) or any(
        len(vector) != settings.embedding_dimension for vector in vectors
    ):
        raise RuntimeError("Embedding output dimension does not match Supabase schema.")
    return [[float(value) for value in vector] for vector in vectors]


def embed_text(text: str) -> list[float]:
    """Convenience wrapper for one string."""
    return embed_texts([text])[0]
