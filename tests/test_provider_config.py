from app.config import Settings


def test_openai_configuration_uses_expected_models_and_dimension():
    settings = Settings(
        supabase_url="https://example.supabase.co",
        supabase_key="server-key",
        openai_api_key="openai-key",
    )

    assert settings.chat_api_key == "openai-key"
    assert settings.chat_model == "gpt-4o-mini"
    assert settings.embedding_model == "text-embedding-3-small"
    assert settings.embedding_dimension == 1536


def test_openai_key_is_the_only_provider_key_required():
    settings = Settings(openai_api_key="")

    assert settings.chat_api_key == ""
    assert settings.chat_model == "gpt-4o-mini"
