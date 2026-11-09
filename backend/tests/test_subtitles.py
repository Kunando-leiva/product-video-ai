"""Tests de subtítulos (Regla 69).

Los tests de transcripción real requieren faster-whisper.
Si no está instalado, se saltan.
"""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.core import ffmpeg
from app.subtitles import stt
from app.subtitles.srt import (
    SubtitleSegment,
    segments_to_srt,
    srt_to_segments,
)


# ----------------------------------------------------------------------
# Tests unitarios del módulo SRT (siempre corren)
# ----------------------------------------------------------------------

def test_srt_roundtrip() -> None:
    segs = [
        SubtitleSegment(index=1, start=0.0, end=1.5, text="Hola mundo"),
        SubtitleSegment(index=2, start=1.5, end=3.25, text="Esto es una prueba"),
    ]
    srt = segments_to_srt(segs)
    assert "00:00:00,000 --> 00:00:01,500" in srt
    assert "Hola mundo" in srt

    parsed = srt_to_segments(srt)
    assert len(parsed) == 2
    assert parsed[0].text == "Hola mundo"
    assert parsed[1].start == 1.5
    assert parsed[1].end == 3.25


def test_srt_handles_crlf() -> None:
    content = "1\r\n00:00:00,000 --> 00:00:01,000\r\nHola\r\n\r\n"
    segs = srt_to_segments(content)
    assert len(segs) == 1
    assert segs[0].text == "Hola"


# ----------------------------------------------------------------------
# API sin transcripción
# ----------------------------------------------------------------------

def test_get_empty(client: TestClient) -> None:
    p = client.post(
        "/api/projects",
        json={"name": "P", "format": "9:16", "duration": 30},
    ).json()
    r = client.get(f"/api/projects/{p['id']}/subtitles")
    assert r.status_code == 200
    assert r.json()["exists"] is False
    assert r.json()["segments"] == []


def test_update_manual(client: TestClient) -> None:
    p = client.post(
        "/api/projects",
        json={"name": "P", "format": "9:16", "duration": 30},
    ).json()

    payload = {
        "segments": [
            {"start": 0.0, "end": 1.0, "text": "Primero"},
            {"start": 1.0, "end": 2.5, "text": "Segundo"},
        ]
    }
    r = client.put(f"/api/projects/{p['id']}/subtitles", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["exists"] is True
    assert len(body["segments"]) == 2
    assert "Primero" in body["srt"]

    # Verificar persistencia
    r2 = client.get(f"/api/projects/{p['id']}/subtitles")
    assert r2.json()["exists"] is True
    assert len(r2.json()["segments"]) == 2


def test_update_empty_rejected(client: TestClient) -> None:
    p = client.post(
        "/api/projects",
        json={"name": "P", "format": "9:16", "duration": 30},
    ).json()
    r = client.put(
        f"/api/projects/{p['id']}/subtitles",
        json={"segments": []},
    )
    assert r.status_code == 422


# ----------------------------------------------------------------------
# Transcripción real (skip si no hay faster-whisper)
# ----------------------------------------------------------------------

@pytest.mark.skipif(
    not stt.is_available() or not ffmpeg.is_available(),
    reason="faster-whisper o FFmpeg no disponibles",
)
def test_transcribe_tts_audio(client: TestClient, tmp_path: Path) -> None:
    """Genera voz con flite y transcribe.

    Nota: flite sintetiza una voz algo robótica, así que usamos el modelo
    'base' (no 'tiny') para que Whisper detecte bien las palabras.
    """
    import shutil
    import subprocess
    from io import BytesIO

    wav = tmp_path / "voice.wav"

    # Intento 1: espeak-ng (si existe en el sistema)
    espeak = shutil.which("espeak-ng") or shutil.which("espeak")
    if espeak:
        subprocess.run(
            [espeak, "-w", str(wav), "hello world this is a test"],
            check=False,
        )
    else:
        # Intento 2: ffmpeg flite (nuestra función helper)
        try:
            ffmpeg.make_test_audio(wav, seconds=2.0)
        except Exception:
            pytest.skip("Sin TTS local disponible para generar voz de prueba")

    if not wav.exists() or wav.stat().st_size == 0:
        pytest.skip("No se pudo generar audio de prueba")

    # Crear proyecto y subir audio
    p = client.post(
        "/api/projects",
        json={"name": "P", "format": "9:16", "duration": 30},
    ).json()
    files = {"file": ("voice.wav", BytesIO(wav.read_bytes()), "audio/wav")}
    up = client.post(f"/api/projects/{p['id']}/media", files=files)
    assert up.status_code == 201, up.text
    media_id = up.json()["id"]

    # Transcribir con modelo base (más robusto con TTS que 'tiny')
    r = client.post(
        f"/api/projects/{p['id']}/subtitles/transcribe",
        json={"media_id": media_id, "model": "base"},
    )
    if r.status_code == 501:
        pytest.skip("faster-whisper no instalado en runtime")
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["segments"]) >= 1
    # flite pronuncia "hello world this is a test" — buscamos "hello" o "world"
    joined = " ".join(s["text"].lower() for s in body["segments"])
    assert "hello" in joined or "world" in joined, joined


# ----------------------------------------------------------------------
# Burn sobre un render
# ----------------------------------------------------------------------

@pytest.mark.skipif(not ffmpeg.is_available(), reason="FFmpeg no disponible")
def test_burn_requires_render(client: TestClient) -> None:
    p = client.post(
        "/api/projects",
        json={"name": "P", "format": "9:16", "duration": 30},
    ).json()
    # Guardar SRT manual
    client.put(
        f"/api/projects/{p['id']}/subtitles",
        json={"segments": [{"start": 0.0, "end": 1.0, "text": "Hola"}]},
    )
    # Sin render → 422
    r = client.post(f"/api/projects/{p['id']}/subtitles/burn", json={})
    assert r.status_code == 422
    assert "render" in r.json()["message"].lower()


@pytest.mark.asyncio
@pytest.mark.skipif(not ffmpeg.is_available(), reason="FFmpeg no disponible")
async def test_burn_end_to_end(async_client: AsyncClient) -> None:
    """Timeline → render → SRT manual → burn.

    El render corre como BackgroundTask de FastAPI, por eso el test
    espera (con polling) hasta 120s a que el job llegue a 'completed'.
    """
    import time
    import tempfile
    from io import BytesIO

    p = (
        await async_client.post(
            "/api/projects",
            json={"name": "P", "format": "9:16", "duration": 30},
        )
    ).json()

    # Subir una imagen
    img = Path(tempfile.mkdtemp()) / "img.png"
    ffmpeg.make_solid_image(img, width=400, height=400, color="blue")
    up = (
        await async_client.post(
            f"/api/projects/{p['id']}/media",
            files={
                "file": ("img.png", BytesIO(img.read_bytes()), "image/png")
            },
        )
    ).json()

    # Timeline con esa imagen
    await async_client.put(
        f"/api/projects/{p['id']}/timeline",
        json={"items": [{"media_id": up["id"], "duration": 2.0}]},
    )

    # Render
    job = (
        await async_client.post(
            f"/api/projects/{p['id']}/render", json={}
        )
    ).json()
    deadline = time.time() + 120
    j = job
    while time.time() < deadline:
        j = (
            await async_client.get(
                f"/api/projects/{p['id']}/render/{job['id']}"
            )
        ).json()
        if j["status"] in ("completed", "failed"):
            break
        time.sleep(0.5)
    assert j["status"] == "completed", j

    # SRT manual
    await async_client.put(
        f"/api/projects/{p['id']}/subtitles",
        json={"segments": [
            {"start": 0.0, "end": 1.0, "text": "PRIMERO"},
            {"start": 1.0, "end": 2.0, "text": "SEGUNDO"},
        ]},
    )

    # Burn
    r = await async_client.post(
        f"/api/projects/{p['id']}/subtitles/burn",
        json={"render_job_id": j["id"]},
    )
    assert r.status_code == 200, r.text
    burned = r.json()
    assert burned["status"] == "completed"
    assert Path(burned["output_path"]).exists()
    assert Path(burned["output_path"]).stat().st_size > 0