import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.auth.dependencies import AuthenticatedUser, get_current_user
from app.security.rate_limit import InMemoryRateLimiter
from app.models.chat import ChatRequest


def test_question_length_is_bounded():
    with pytest.raises(ValueError):
        ChatRequest(question="x" * 2001)



def test_missing_bearer_token_is_rejected():
    with pytest.raises(HTTPException) as exc:
        get_current_user(None)
    assert exc.value.status_code == 401


def test_malformed_bearer_token_is_rejected():
    credentials = HTTPAuthorizationCredentials(scheme="Basic", credentials="token")
    with pytest.raises(HTTPException) as exc:
        get_current_user(credentials)
    assert exc.value.status_code == 401


def test_invalid_supabase_token_is_rejected_without_provider_details(monkeypatch):
    class Auth:
        def get_user(self, token):
            raise RuntimeError("provider internals")

    monkeypatch.setattr("app.auth.dependencies.get_client", lambda: type("Client", (), {"auth": Auth()})())
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad-token")
    with pytest.raises(HTTPException) as exc:
        get_current_user(credentials)
    assert exc.value.status_code == 401
    assert "provider internals" not in str(exc.value.detail)


def test_valid_supabase_token_returns_user_id(monkeypatch):
    class User:
        id = "user-a"

    class Auth:
        def get_user(self, token):
            assert token == "access-token"
            return type("Response", (), {"user": User()})()

    monkeypatch.setattr("app.auth.dependencies.get_client", lambda: type("Client", (), {"auth": Auth()})())
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="access-token")
    assert get_current_user(credentials) == AuthenticatedUser(id="user-a")


def test_rate_limiter_rejects_after_limit_and_resets(monkeypatch):
    now = [100.0]
    monkeypatch.setattr("app.security.rate_limit.time.monotonic", lambda: now[0])
    limiter = InMemoryRateLimiter(max_requests=2, window_seconds=60)
    assert limiter.allow("user-a")
    assert limiter.allow("user-a")
    assert not limiter.allow("user-a")
    now[0] = 161.0
    assert limiter.allow("user-a")


def test_rate_limiter_evicts_old_keys(monkeypatch):
    monkeypatch.setattr("app.security.rate_limit.time.monotonic", lambda: 100.0)
    limiter = InMemoryRateLimiter(max_requests=1, window_seconds=60, max_keys=2)
    assert limiter.allow("user-a")
    assert limiter.allow("user-b")
    assert limiter.allow("user-c")
    assert len(limiter._requests) == 2
