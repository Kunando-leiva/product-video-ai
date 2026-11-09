"""Tests de carga/listado/borrado de media."""
from io import BytesIO
from typing import Any
from httpx import Response
from fastapi.testclient import TestClient

from httpx import Response
from fastapi.testclient import TestClient


PNG_1x1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c6360000002000154a24f9d00000000"
    "49454e44ae426082"
)


def _create_project(client: TestClient, name: str = "P") -> dict[str, Any]:
    r = client.post(
        "/api/projects",
        json={"name": name, "format": "9:16", "duration": 30},
    )
    assert r.status_code == 201
    return r.json()


def _upload(
    client: TestClient,
    project_id: str,
    filename: str,
    content: bytes,
    content_type: str = "application/octet-stream",
) -> Response:   # ← antes decía "-> dict", ahora Response
    files = {"file": (filename, BytesIO(content), content_type)}
    r = client.post(f"/api/projects/{project_id}/media", files=files)
    return r


def test_upload_image(client: TestClient) -> None:
    p = _create_project(client)
    r = _upload(client, p["id"], "foto.png", PNG_1x1, "image/png")
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["type"] == "image"
    assert body["original_name"] == "foto.png"
    assert body["url"].startswith("/projects/")
    assert body["url"].endswith(".png")


def test_upload_video_by_extension(client: TestClient) -> None:
    p = _create_project(client)
    r = _upload(client, p["id"], "clip.mp4", b"fake-mp4-bytes", "video/mp4")
    assert r.status_code == 201
    assert r.json()["type"] == "video"


def test_upload_audio(client: TestClient) -> None:
    p = _create_project(client)
    r = _upload(client, p["id"], "track.mp3", b"fake-mp3", "audio/mpeg")
    assert r.status_code == 201
    assert r.json()["type"] == "audio"


def test_upload_rejects_unknown_extension(client: TestClient) -> None:
    p = _create_project(client)
    r = _upload(client, p["id"], "script.exe", b"MZ", "application/octet-stream")
    assert r.status_code == 422
    assert r.json()["error"] == "validation_error"


def test_upload_rejects_empty(client: TestClient) -> None:
    p = _create_project(client)
    r = _upload(client, p["id"], "foto.png", b"", "image/png")
    assert r.status_code == 422


def test_upload_sanitizes_name(client: TestClient) -> None:
    p = _create_project(client)
    r = _upload(client, p["id"], "../../etc/passwd.png", PNG_1x1, "image/png")
    assert r.status_code == 201
    # El nombre original queda solo como basename
    assert "/" not in r.json()["original_name"]
    assert ".." not in r.json()["original_name"]


def test_list_media(client: TestClient) -> None:
    p = _create_project(client)
    _upload(client, p["id"], "a.png", PNG_1x1, "image/png")
    _upload(client, p["id"], "b.mp4", b"bytes", "video/mp4")
    r = client.get(f"/api/projects/{p['id']}/media")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    assert {m["type"] for m in data} == {"image", "video"}


def test_list_media_unknown_project(client: TestClient) -> None:
    r = client.get("/api/projects/project_nope/media")
    assert r.status_code == 404


def test_delete_media(client: TestClient) -> None:
    p = _create_project(client)
    up = _upload(client, p["id"], "foto.png", PNG_1x1, "image/png").json()
    r = client.delete(f"/api/projects/{p['id']}/media/{up['id']}")
    assert r.status_code == 204
    r2 = client.get(f"/api/projects/{p['id']}/media")
    assert r2.json() == []


def test_delete_unknown_media(client: TestClient) -> None:
    p = _create_project(client)
    r = client.delete(f"/api/projects/{p['id']}/media/media_nope")
    assert r.status_code == 404