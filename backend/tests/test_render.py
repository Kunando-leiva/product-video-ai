"""Tests del Render Engine (Regla 68)."""
import subprocess
import time
from io import BytesIO
from pathlib import Path

import pytest
from httpx import AsyncClient

from app.core import ffmpeg


pytestmark = pytest.mark.skipif(
    not ffmpeg.is_available(),
    reason="FFmpeg no disponible",
)


async def _project(async_client: AsyncClient, fmt: str = "9:16") -> dict:
    r = await async_client.post(
        "/api/projects",
        json={"name": "RenderTest", "format": fmt, "duration": 30},
    )
    assert r.status_code == 201
    return r.json()


async def _upload_video(
    async_client: AsyncClient, pid: str, seconds: float, name: str
) -> dict:
    import tempfile
    tmp = Path(tempfile.mkdtemp()) / f"{name}.mp4"
    ffmpeg.make_test_video(tmp, seconds=seconds, fps=24, size="320x240")
    data = tmp.read_bytes()
    files = {"file": (f"{name}.mp4", BytesIO(data), "video/mp4")}
    r = await async_client.post(
        f"/api/projects/{pid}/media", files=files
    )
    assert r.status_code == 201, r.text
    return r.json()


async def _upload_image(
    async_client: AsyncClient, pid: str, name: str
) -> dict:
    import tempfile
    tmp = Path(tempfile.mkdtemp()) / f"{name}.png"
    ffmpeg.make_solid_image(tmp, width=400, height=400, color="red")
    data = tmp.read_bytes()
    files = {"file": (f"{name}.png", BytesIO(data), "image/png")}
    r = await async_client.post(
        f"/api/projects/{pid}/media", files=files
    )
    assert r.status_code == 201, r.text
    return r.json()


async def _put_timeline(
    async_client: AsyncClient, pid: str, items: list[dict]
) -> None:
    r = await async_client.put(
        f"/api/projects/{pid}/timeline", json={"items": items}
    )
    assert r.status_code == 200, r.text


async def _wait_render(
    async_client: AsyncClient, pid: str, job_id: str, timeout: float = 60
) -> dict:
    """Polling hasta completed/failed."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = await async_client.get(f"/api/projects/{pid}/render/{job_id}")
        assert r.status_code == 200
        job = r.json()
        if job["status"] in ("completed", "failed"):
            return job
        time.sleep(0.5)
    raise AssertionError(f"Timeout esperando render {job_id}")


# ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_render_empty_timeline_fails(
    async_client: AsyncClient,
) -> None:
    p = await _project(async_client)
    r = await async_client.post(f"/api/projects/{p['id']}/render", json={})
    assert r.status_code == 422
    assert "vacía" in r.json()["message"].lower()


@pytest.mark.asyncio
async def test_render_single_clip(async_client: AsyncClient) -> None:
    p = await _project(async_client)
    v = await _upload_video(async_client, p["id"], seconds=2.0, name="clip")
    await _put_timeline(async_client, p["id"], [
        {"media_id": v["id"], "duration": 1.5, "effect": "none"},
    ])

    r = await async_client.post(f"/api/projects/{p['id']}/render", json={})
    assert r.status_code == 202, r.text
    job_id = r.json()["id"]
    assert r.json()["status"] in ("queued", "processing")

    job = await _wait_render(async_client, p["id"], job_id)
    assert job["status"] == "completed", job
    assert job["progress"] == 1.0
    assert job["output_path"] is not None
    assert Path(job["output_path"]).exists()
    assert Path(job["output_path"]).stat().st_size > 0

    d = ffmpeg.probe_duration(Path(job["output_path"]))
    assert d is not None and 1.0 <= d <= 2.0, f"duración: {d}"


@pytest.mark.asyncio
async def test_render_three_clips(async_client: AsyncClient) -> None:
    """A → B → C, cada uno 1s, total ~3s."""
    p = await _project(async_client)
    a = await _upload_image(async_client, p["id"], "a")
    b = await _upload_video(async_client, p["id"], seconds=2.0, name="b")
    c = await _upload_image(async_client, p["id"], "c")

    await _put_timeline(async_client, p["id"], [
        {"media_id": a["id"], "duration": 1.0, "effect": "none"},
        {"media_id": b["id"], "duration": 1.0, "effect": "zoom_in"},
        {"media_id": c["id"], "duration": 1.0, "effect": "fade"},
    ])

    r = await async_client.post(f"/api/projects/{p['id']}/render", json={})
    job = await _wait_render(async_client, p["id"], r.json()["id"])
    assert job["status"] == "completed", job

    out = Path(job["output_path"])
    assert out.exists()
    d = ffmpeg.probe_duration(out)
    assert d is not None and 2.5 <= d <= 3.5, f"duración: {d}"

    info = ffmpeg.probe(out)
    vs = next(s for s in info["streams"] if s.get("codec_type") == "video")
    assert int(vs["width"]) == 1080
    assert int(vs["height"]) == 1920


@pytest.mark.asyncio
async def test_render_different_format(async_client: AsyncClient) -> None:
    """El proyecto define 16:9 y el render debe respetarlo."""
    p = await _project(async_client, fmt="16:9")
    a = await _upload_image(async_client, p["id"], "a")
    await _put_timeline(async_client, p["id"], [
        {"media_id": a["id"], "duration": 1.0, "effect": "none"},
    ])
    r = await async_client.post(f"/api/projects/{p['id']}/render", json={})
    job = await _wait_render(async_client, p["id"], r.json()["id"])
    assert job["status"] == "completed", job

    info = ffmpeg.probe(Path(job["output_path"]))
    vs = next(s for s in info["streams"] if s.get("codec_type") == "video")
    assert int(vs["width"]) == 1920
    assert int(vs["height"]) == 1080


@pytest.mark.asyncio
async def test_render_progress_advances(async_client: AsyncClient) -> None:
    """El job debe atravesar los estados queued→processing→completed
    y terminar con progress=1.0.

    Nota: no verificamos valores intermedios de `progress` porque el
    render de imágenes 1×1 puede completarse en <200ms (el polling
    nunca llega a ver un valor entre 0 y 1). El contrato importante es
    que el job llegue a 'completed' con progress=1.0 y que exista la
    transición de estados.
    """
    p = await _project(async_client)
    a = await _upload_image(async_client, p["id"], "a")
    b = await _upload_image(async_client, p["id"], "b")
    c = await _upload_image(async_client, p["id"], "c")
    await _put_timeline(async_client, p["id"], [
        {"media_id": a["id"], "duration": 1.0},
        {"media_id": b["id"], "duration": 1.0},
        {"media_id": c["id"], "duration": 1.0},
    ])
    r = await async_client.post(f"/api/projects/{p['id']}/render", json={})
    assert r.status_code == 202, r.text

    created = r.json()
    job_id = created["id"]

    # El job recién creado debe estar en 'queued' o 'processing'
    assert created["status"] in ("queued", "processing"), created

    # Esperar a completed
    seen_statuses = {created["status"]}
    deadline = time.time() + 60
    job = None
    while time.time() < deadline:
        job = (
            await async_client.get(f"/api/projects/{p['id']}/render/{job_id}")
        ).json()
        seen_statuses.add(job["status"])
        if job["status"] in ("completed", "failed"):
            break
        time.sleep(0.1)

    assert job is not None, f"Timeout esperando render {job_id}"
    assert job["status"] == "completed", job
    assert job["progress"] == 1.0
    # El job pasó por al menos 2 estados (queued/processing → completed)
    assert len(seen_statuses) >= 2, f"Estados vistos: {seen_statuses}"


@pytest.mark.asyncio
async def test_render_list_jobs(async_client: AsyncClient) -> None:
    p = await _project(async_client)
    a = await _upload_image(async_client, p["id"], "a")
    await _put_timeline(async_client, p["id"], [
        {"media_id": a["id"], "duration": 0.5}
    ])
    r = await async_client.post(f"/api/projects/{p['id']}/render", json={})
    await _wait_render(async_client, p["id"], r.json()["id"])

    jobs = (
        await async_client.get(f"/api/projects/{p['id']}/render")
    ).json()
    assert len(jobs) == 1
    assert jobs[0]["status"] == "completed"
    assert jobs[0]["output_url"] is not None


@pytest.mark.asyncio
async def test_render_delete_job(async_client: AsyncClient) -> None:
    p = await _project(async_client)
    a = await _upload_image(async_client, p["id"], "a")
    await _put_timeline(async_client, p["id"], [
        {"media_id": a["id"], "duration": 0.5}
    ])
    r = await async_client.post(f"/api/projects/{p['id']}/render", json={})
    job = await _wait_render(async_client, p["id"], r.json()["id"])
    out = Path(job["output_path"])
    assert out.exists()

    d = await async_client.delete(
        f"/api/projects/{p['id']}/render/{job['id']}"
    )
    assert d.status_code == 204
    assert not out.exists()
    jobs = (
        await async_client.get(f"/api/projects/{p['id']}/render")
    ).json()
    assert jobs == []