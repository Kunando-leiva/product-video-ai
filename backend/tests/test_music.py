"""Tests del sistema de música (Regla 71)."""
import subprocess
import time
from io import BytesIO
from pathlib import Path

import pytest
from httpx import AsyncClient

from app.core import ffmpeg
from app.audio.music import music_dir


pytestmark = pytest.mark.skipif(
    not ffmpeg.is_available(),
    reason="FFmpeg no disponible",
)


@pytest.fixture
def sample_music() -> Path:
    """Genera una pista corta de música de prueba."""
    d = music_dir()
    d.mkdir(parents=True, exist_ok=True)
    out = d / "test_track.mp3"
    if not out.exists():
        subprocess.run(
            [
                ffmpeg.ffmpeg_path() or "ffmpeg", "-y",
                "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
                "-c:a", "libmp3lame", "-b:a", "96k",
                str(out),
            ],
            capture_output=True,
        )
    return out


@pytest.mark.asyncio
async def test_list_music_tracks(
    async_client: AsyncClient, sample_music: Path
) -> None:
    r = await async_client.get("/api/music/tracks")
    assert r.status_code == 200
    tracks = r.json()["tracks"]
    assert any(t["id"] == "test_track" for t in tracks)
    t = next(x for x in tracks if x["id"] == "test_track")
    assert t["url"] is not None
    assert t["url"].endswith(".mp3")


@pytest.mark.asyncio
async def test_set_music_selection(
    async_client: AsyncClient, sample_music: Path
) -> None:
    p = (
        await async_client.post(
            "/api/projects",
            json={"name": "P", "format": "9:16", "duration": 30},
        )
    ).json()

    r = await async_client.put(
        f"/api/projects/{p['id']}/music",
        json={
            "music_track": "test_track",
            "music_volume": 0.12,
            "music_enabled": True,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["music_track"] == "test_track"
    assert body["music_volume"] == 0.12
    assert body["music_enabled"] is True

    # Persistencia
    r2 = await async_client.get(f"/api/projects/{p['id']}/music")
    assert r2.json()["music_track"] == "test_track"


@pytest.mark.asyncio
async def test_set_invalid_music_rejected(
    async_client: AsyncClient,
) -> None:
    p = (
        await async_client.post(
            "/api/projects",
            json={"name": "P", "format": "9:16", "duration": 30},
        )
    ).json()
    r = await async_client.put(
        f"/api/projects/{p['id']}/music",
        json={"music_track": "no_existe_xxx"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_disable_music(
    async_client: AsyncClient, sample_music: Path
) -> None:
    p = (
        await async_client.post(
            "/api/projects",
            json={"name": "P", "format": "9:16", "duration": 30},
        )
    ).json()
    await async_client.put(
        f"/api/projects/{p['id']}/music",
        json={"music_track": "test_track"},
    )
    r = await async_client.put(
        f"/api/projects/{p['id']}/music",
        json={"music_enabled": False},
    )
    assert r.json()["music_enabled"] is False


@pytest.mark.asyncio
async def test_render_with_music_only(
    async_client: AsyncClient, sample_music: Path, tmp_path: Path
) -> None:
    """Video + música → MP4 con stream de audio."""
    p = (
        await async_client.post(
            "/api/projects",
            json={"name": "P", "format": "9:16", "duration": 30},
        )
    ).json()

    # Media — usar tmp_path (cross-platform)
    img = tmp_path / "test_img.png"
    ffmpeg.make_solid_image(img, 400, 400, "red")
    up = (
        await async_client.post(
            f"/api/projects/{p['id']}/media",
            files={
                "file": ("img.png", BytesIO(img.read_bytes()), "image/png")
            },
        )
    ).json()

    # Timeline
    await async_client.put(
        f"/api/projects/{p['id']}/timeline",
        json={"items": [{"media_id": up["id"], "duration": 2.0}]},
    )

    # Seleccionar música
    await async_client.put(
        f"/api/projects/{p['id']}/music",
        json={"music_track": "test_track", "music_volume": 0.2},
    )

    # Render
    job = (
        await async_client.post(
            f"/api/projects/{p['id']}/render", json={}
        )
    ).json()
    deadline = time.time() + 60
    j = None
    while time.time() < deadline:
        j = (
            await async_client.get(
                f"/api/projects/{p['id']}/render/{job['id']}"
            )
        ).json()
        if j["status"] in ("completed", "failed"):
            break
        time.sleep(0.5)

    assert j is not None
    assert j["status"] == "completed", j
    out = Path(j["output_path"])
    info = ffmpeg.probe(out)
    types = [s.get("codec_type") for s in info["streams"]]
    assert "audio" in types, types
    assert "video" in types


@pytest.mark.asyncio
async def test_render_with_voice_and_music(
    async_client: AsyncClient, sample_music: Path, tmp_path: Path
) -> None:
    """Voz + música → MP4 con audio mezclado."""
    from app.core.paths import project_dir

    p = (
        await async_client.post(
            "/api/projects",
            json={"name": "P", "format": "9:16", "duration": 30},
        )
    ).json()

    # Media visual
    img = tmp_path / "test_img2.png"
    ffmpeg.make_solid_image(img, 400, 400, "green")
    up = (
        await async_client.post(
            f"/api/projects/{p['id']}/media",
            files={
                "file": ("img.png", BytesIO(img.read_bytes()), "image/png")
            },
        )
    ).json()

    await async_client.put(
        f"/api/projects/{p['id']}/timeline",
        json={"items": [{"media_id": up["id"], "duration": 2.0}]},
    )

    # Generar voz de prueba en tmp_path
    voice = tmp_path / "test_voice.wav"
    subprocess.run(
        [
            ffmpeg.ffmpeg_path() or "ffmpeg", "-y",
            "-f", "lavfi", "-i", "sine=frequency=800:duration=2",
            "-ac", "1", "-ar", "16000", str(voice),
        ],
        capture_output=True,
        check=True,
    )

    # Copiar a la carpeta audio/ del proyecto
    audio_dir = project_dir(p["id"]) / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    voice_target = audio_dir / "voice_test.wav"
    voice_target.write_bytes(voice.read_bytes())

    # Configurar voz y música
    await async_client.put(
        f"/api/projects/{p['id']}/music",
        json={
            "music_track": "test_track",
            "music_volume": 0.15,
            "music_enabled": True,
            "voice_track": f"/projects/{p['id']}/audio/voice_test.wav",
            "voice_enabled": True,
        },
    )

    # Render
    job = (
        await async_client.post(
            f"/api/projects/{p['id']}/render", json={}
        )
    ).json()
    deadline = time.time() + 60
    j = None
    while time.time() < deadline:
        j = (
            await async_client.get(
                f"/api/projects/{p['id']}/render/{job['id']}"
            )
        ).json()
        if j["status"] in ("completed", "failed"):
            break
        time.sleep(0.5)

    assert j is not None
    assert j["status"] == "completed", j
    out = Path(j["output_path"])
    info = ffmpeg.probe(out)
    types = [s.get("codec_type") for s in info["streams"]]
    assert "audio" in types
    assert "video" in types
    # Duración ≈ 2s
    d = ffmpeg.probe_duration(out)
    assert d is not None and 1.5 <= d <= 2.5