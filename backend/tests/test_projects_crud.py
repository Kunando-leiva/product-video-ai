"""Tests de integración del CRUD de proyectos."""
from fastapi.testclient import TestClient


def _create(client: TestClient, name: str = "Auriculares X200") -> dict:
    r = client.post(
        "/api/projects",
        json={
            "name": name,
            "product_url": "https://ejemplo.com/p/1",
            "format": "9:16",
            "duration": 30,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_create_project(client: TestClient) -> None:
    p = _create(client)
    assert p["id"].startswith("project_")
    assert p["name"] == "Auriculares X200"
    assert p["format"] == "9:16"
    assert p["duration"] == 30
    assert p["product_url"] == "https://ejemplo.com/p/1"


def test_list_projects(client: TestClient) -> None:
    _create(client, "Uno")
    _create(client, "Dos")
    r = client.get("/api/projects")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2


def test_get_project(client: TestClient) -> None:
    created = _create(client, "Producto A")
    r = client.get(f"/api/projects/{created['id']}")
    assert r.status_code == 200
    assert r.json()["name"] == "Producto A"


def test_update_project(client: TestClient) -> None:
    p = _create(client)
    r = client.put(
        f"/api/projects/{p['id']}",
        json={"name": "Nuevo nombre", "duration": 60},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["name"] == "Nuevo nombre"
    assert data["duration"] == 60


def test_delete_project(client: TestClient) -> None:
    p = _create(client)
    r = client.delete(f"/api/projects/{p['id']}")
    assert r.status_code == 204

    r2 = client.get(f"/api/projects/{p['id']}")
    assert r2.status_code == 404


def test_invalid_format_rejected(client: TestClient) -> None:
    r = client.post(
        "/api/projects",
        json={"name": "X", "format": "3:2", "duration": 30},
    )
    assert r.status_code == 422


def test_invalid_duration_rejected(client: TestClient) -> None:
    r = client.post(
        "/api/projects",
        json={"name": "X", "format": "9:16", "duration": 45},
    )
    assert r.status_code == 422