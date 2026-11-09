"""Tests de voz IA (Regla 70)."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.audio.tts_local import LocalPiperTTS
from app.audio.voices import list_voices


# ----------------------------------------------------------------------
# Sin piper instalado
# ----------------------------------------------------------------------

def test_voices_endpoint(client: TestClient) -> None:
    r = client.get("/api/voice/voices")
    assert r.status_code == 200
    body = r.json()
    assert "available" in body
    assert "provider" in body
    assert isinstance(body["voices"], list)


def test_synthesize_empty_text_rejected(client: TestClient) -> None:
    p = client.post(
        "/api/projects",
        json={"name": "P", "format": "9:16", "duration": 30},
    ).json()
    r = client.post(
        f"/api/projects/{p['id']}/voice/synthesize",
        json={"text": ""},
    )
    assert r.status_code == 422


# ----------------------------------------------------------------------
# Con piper instalado
# ----------------------------------------------------------------------

pytestmark_available = pytest.mark.skipif(
    not LocalPiperTTS().is_available(),
    reason="piper-tts no instalado o sin voces",
)


@pytestmark_available
def test_synthesize_real(client: TestClient) -> None:
    p = client.post(
        "/api/projects",
        json={"name": "P", "format": "9:16", "duration": 30},
    ).json()

    r = client.post(
        f"/api/projects/{p['id']}/voice/synthesize",
        json={"text": "Este es un producto increíble."},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert Path(body["audio_path"]).exists()
    assert body["size_bytes"] > 1000
    assert body["audio_url"].endswith(".wav")
    if body["duration"] is not None:
        assert 0.5 <= body["duration"] <= 10.0


@pytestmark_available
def test_synthesize_specific_voice(client: TestClient) -> None:
    voices = list_voices()
    if not voices:
        pytest.skip("sin voces")
    vid = voices[0].id

    p = client.post(
        "/api/projects",
        json={"name": "P", "format": "9:16", "duration": 30},
    ).json()
    r = client.post(
        f"/api/projects/{p['id']}/voice/synthesize",
        json={"text": "Hola mundo", "voice_id": vid},
    )
    assert r.status_code == 200
    assert Path(r.json()["audio_path"]).exists()


@pytestmark_available
def test_synthesize_unknown_voice(client: TestClient) -> None:
    p = client.post(
        "/api/projects",
        json={"name": "P", "format": "9:16", "duration": 30},
    ).json()
    r = client.post(
        f"/api/projects/{p['id']}/voice/synthesize",
        json={"text": "Hola", "voice_id": "no-existe-xxx"},
    )
    assert r.status_code == 404