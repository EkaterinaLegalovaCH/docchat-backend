"""
OpenAI embedding generation.

Uses the OpenAI API to turn text chunks into vector embeddings
that can be searched with cosine similarity.
"""

from openai import OpenAI
from typing import List

from app.config import settings


def get_client() -> OpenAI:
    """Return an authenticated OpenAI client (reads API key from settings)."""
    return OpenAI(api_key=settings.openai_api_key)


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Embed a list of text strings into vectors.

    Returns a list of vectors, each vector being a list of floats.
    The model is configured in settings.embedding_model.
    """
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is not set — cannot generate embeddings.")

    client = get_client()
    response = client.embeddings.create(
        model=settings.embedding_model,
        input=texts,
    )
    # Sort by index so we return in the same order as input
    ordered = sorted(response.data, key=lambda x: x.index)
    return [item.embedding for item in ordered]


def embed_text(text: str) -> List[float]:
    """Convenience: embed a single text string."""
    return embed_texts([text])[0]