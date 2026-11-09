"""Verifica el formato estándar de errores (Regla 47)."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)


def test_not_implemented_settings() -> None:
    r = client.get("/api/settings")
    assert r.status_code == 501
    body = r.json()
    assert body["error"] == "not_implemented"


def test_404_returns_structured_error() -> None:
    r = client.get("/api/does-not-exist")
    assert r.status_code == 404
    body = r.json()
    assert body["error"] == "not_found"
    assert "message" in body


def test_get_unknown_project_404(client: TestClient) -> None:
    r = client.get("/api/projects/project_nope")
    assert r.status_code == 404
    body = r.json()
    assert body["error"] == "not_found"