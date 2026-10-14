from fastapi.testclient import TestClient
from app.main import app


def test_health_is_cheap_and_available_without_credentials():
    response = TestClient(app).get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_protected_routes_require_authentication():
    client = TestClient(app)
    assert client.get("/api/documents").status_code == 401
    assert client.post("/api/chat/ask", json={"question": "hello"}).status_code == 401


def test_ready_reports_missing_configuration_without_crashing(monkeypatch):
    monkeypatch.setattr("app.main.settings.supabase_url", "")
    monkeypatch.setattr("app.main.settings.supabase_key", "")
    monkeypatch.setattr("app.main.settings.openai_api_key", "")

    response = TestClient(app).get("/api/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "not_ready"
    assert "SUPABASE_URL" in response.json()["missing"]
    assert "OPENAI_API_KEY" in response.json()["missing"]
