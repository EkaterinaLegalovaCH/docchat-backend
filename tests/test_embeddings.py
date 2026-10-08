import pytest

from app.config import Settings
from app.services import embeddings


def test_default_embedding_configuration_uses_openai_model_and_dimension():
    settings = Settings()

    assert settings.embedding_model == "text-embedding-3-small"
    assert settings.embedding_dimension == 1536


def test_embedding_service_rejects_unexpected_dimension(monkeypatch):
    class FakeEmbeddings:
        def create(self, **kwargs):
            class Item:
                embedding = [0.0] * 3

            class Response:
                data = [Item()]

            return Response()

    class FakeClient:
        embeddings = FakeEmbeddings()

    monkeypatch.setattr(embeddings, "OpenAI", lambda **kwargs: FakeClient())
    monkeypatch.setattr(embeddings.settings, "openai_api_key", "test-key")

    with pytest.raises(RuntimeError, match="dimension"):
        embeddings.embed_text("test")


def test_embedding_readiness_does_not_make_network_request(monkeypatch):
    monkeypatch.setattr(embeddings.settings, "openai_api_key", "")

    assert embeddings.readiness() == {
        "available": False,
        "model": "text-embedding-3-small",
        "dimension": 1536,
    }
