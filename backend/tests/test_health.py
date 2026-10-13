from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_cors_allows_configured_dev_origin():
    response = client.options("/health", headers={
        "Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"})
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_rejects_unknown_origin():
    response = client.options("/health", headers={
        "Origin": "https://evil.example", "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in response.headers
