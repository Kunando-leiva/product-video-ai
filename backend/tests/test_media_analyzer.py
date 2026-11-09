"""Tests del Media Analyzer (Regla 65)."""
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core import ffmpeg


pytestmark = pytest.mark.skipif(
    not ffmpeg.is_available(),
    reason="FFmpeg no disponible",
)


def _create_project(client: TestClient, name: str = "P") -> dict:
    r = client.post(
        "/api/projects",
        json={"name": name, "format": "9:16", "duration": 30},
    )
    assert r.status_code == 201
    return r.json()


def _upload(
    client: TestClient, project_id: str, path: Path, content_type: str
) -> dict:
    data = path.read_bytes()
    files = {"file": (path.name, BytesIO(data), content_type)}
    r = client.post(f"/api/projects/{project_id}/media", files=files)
    assert r.status_code == 201, r.text
    return r.json()


def test_video_metadata(client: TestClient, sample_video: Path) -> None:
    p = _create_project(client)
    m = _upload(client, p["id"], sample_video, "video/mp4")

    assert m["type"] == "video"
    assert m["duration"] is not None
    assert 1.5 <= m["duration"] <= 2.5, f"duración inesperada: {m['duration']}"
    assert m["width"] == 320
    assert m["height"] == 240
    assert m["fps"] is not None
    assert 20 <= m["fps"] <= 30, f"fps inesperados: {m['fps']}"
    assert m["orientation"] == "horizontal"


def test_video_thumbnail_generated(client: TestClient, sample_video: Path) -> None:
    p = _create_project(client)
    m = _upload(client, p["id"], sample_video, "video/mp4")

    assert m["thumbnail_path"] is not None
    assert m["thumbnail_url"] is not None
    assert Path(m["thumbnail_path"]).exists()


def test_image_metadata(client: TestClient, sample_image: Path) -> None:
    p = _create_project(client)
    m = _upload(client, p["id"], sample_image, "image/png")

    assert m["type"] == "image"
    assert m["width"] == 640
    assert m["height"] == 480
    assert m["orientation"] == "horizontal"
    # Imágenes no tienen fps ni thumbnail propio
    assert m["fps"] is None
    assert m["thumbnail_path"] is None


def test_vertical_orientation(client: TestClient, tmp_path: Path) -> None:
    if not ffmpeg.is_available():
        pytest.skip("FFmpeg no disponible")
    # Video vertical 240x320
    v = tmp_path / "vertical.mp4"
    ffmpeg.make_test_video(v, seconds=1.0, fps=24, size="240x320")

    p = _create_project(client)
    m = _upload(client, p["id"], v, "video/mp4")
    assert m["orientation"] == "vertical"


def test_square_orientation(client: TestClient, tmp_path: Path) -> None:
    if not ffmpeg.is_available():
        pytest.skip("FFmpeg no disponible")
    v = tmp_path / "square.mp4"
    ffmpeg.make_test_video(v, seconds=1.0, fps=24, size="300x300")

    p = _create_project(client)
    m = _upload(client, p["id"], v, "video/mp4")
    assert m["orientation"] == "square"


def test_reanalyze_endpoint(client: TestClient, sample_video: Path) -> None:
    p = _create_project(client)
    m = _upload(client, p["id"], sample_video, "video/mp4")
    r = client.post(f"/api/projects/{p['id']}/media/{m['id']}/analyze")
    assert r.status_code == 200
    body = r.json()
    assert body["duration"] is not None
    assert body["width"] == 320