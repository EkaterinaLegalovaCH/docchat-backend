from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_protected_routes_require_bearer_token():
    assert client.get("/api/documents").status_code == 401
    assert client.post("/api/documents/upload").status_code == 401
    assert client.delete("/api/documents/not-a-document").status_code == 401
    assert client.post("/api/chat/ask", json={"question": "hello"}).status_code == 401
