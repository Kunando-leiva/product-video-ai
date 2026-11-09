"""Tests de la interfaz de IA (Regla 72)."""
import json

import pytest
from fastapi.testclient import TestClient

from app.ai.mock_provider import MockProvider
from app.ai.provider import (
    AIScriptRequest,
    AITextRequest,
)


# ----------------------------------------------------------------------
# Tests unitarios del MockProvider
# ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mock_is_available() -> None:
    assert MockProvider().is_available() is True


@pytest.mark.asyncio
async def test_mock_generate_text() -> None:
    p = MockProvider()
    resp = await p.generate_text(AITextRequest(prompt="Hola mundo"))
    assert "[MOCK]" in resp.text
    assert resp.provider == "mock"
    assert resp.tokens_in > 0


@pytest.mark.asyncio
async def test_mock_generate_text_json_schema() -> None:
    p = MockProvider()
    schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "score": {"type": "number"},
            "tags": {"type": "array", "items": {"type": "string"}},
        },
    }
    resp = await p.generate_text(
        AITextRequest(prompt="genera", json_schema=schema)
    )
    data = json.loads(resp.text)
    assert "title" in data
    assert isinstance(data["score"], float)
    assert isinstance(data["tags"], list)


@pytest.mark.asyncio
async def test_mock_analyze_image() -> None:
    p = MockProvider()
    a = await p.analyze_image("/tmp/x.png")
    assert a.is_product is True
    assert "product" in a.tags
    assert a.provider == "mock"


@pytest.mark.asyncio
async def test_mock_analyze_video() -> None:
    p = MockProvider()
    a = await p.analyze_video("/tmp/x.mp4")
    assert len(a.scenes) >= 1
    assert a.provider == "mock"


@pytest.mark.asyncio
async def test_mock_generate_script() -> None:
    p = MockProvider()
    s = await p.generate_script(
        AIScriptRequest(
            product_name="Auriculares X200",
            product_description="Sonido premium",
            duration=30,
        )
    )
    assert s.hook
    assert s.cta
    assert len(s.sections) >= 1
    total = sum(sec.duration for sec in s.sections)
    # El cuerpo + hook + cta debería acercarse a la duración pedida
    assert 20 <= total + 30 * 0.35 <= 40  # ~30s aprox


# ----------------------------------------------------------------------
# Tests HTTP (usan TestClient sync — no BackgroundTasks)
# ----------------------------------------------------------------------

def test_list_providers(client: TestClient) -> None:
    r = client.get("/api/ai/providers")
    assert r.status_code == 200
    body = r.json()
    assert body["active"] == "mock"
    names = {p["name"] for p in body["providers"]}
    assert "mock" in names
    mock = next(p for p in body["providers"] if p["name"] == "mock")
    assert mock["available"] is True
    assert mock["requires_internet"] is False


def test_provider_detail_ok(client: TestClient) -> None:
    r = client.get("/api/ai/providers/mock")
    assert r.status_code == 200
    assert r.json()["name"] == "mock"


def test_provider_detail_404(client: TestClient) -> None:
    r = client.get("/api/ai/providers/noexiste")
    assert r.status_code == 404
    assert r.json()["error"] == "not_found"


def test_test_text(client: TestClient) -> None:
    r = client.post(
        "/api/ai/test/text",
        json={"prompt": "Decime algo sobre auriculares"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "[MOCK]" in body["text"]
    assert body["provider"] == "mock"
    assert body["tokens_in"] > 0


def test_test_text_json_schema(client: TestClient) -> None:
    r = client.post(
        "/api/ai/test/text",
        json={
            "prompt": "estructurado",
            "json_schema": {
                "type": "object",
                "properties": {
                    "hook": {"type": "string"},
                    "score": {"type": "integer"},
                },
            },
        },
    )
    assert r.status_code == 200
    data = json.loads(r.json()["text"])
    assert "hook" in data
    assert "score" in data


def test_test_script(client: TestClient) -> None:
    r = client.post(
        "/api/ai/test/script",
        json={
            "product_name": "Auriculares X200",
            "product_description": "Sonido premium",
            "duration": 30,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["hook"]
    assert body["cta"]
    assert len(body["sections"]) >= 1


def test_usage_recorded(client: TestClient) -> None:
    # Hacer 2 llamadas
    client.post("/api/ai/test/text", json={"prompt": "uno"})
    client.post("/api/ai/test/script", json={"product_name": "P", "duration": 30})

    r = client.get("/api/ai/usage?limit=10")
    assert r.status_code == 200
    rows = r.json()["rows"]
    assert len(rows) >= 2
    tasks = {row["task"] for row in rows}
    assert "generate_text" in tasks
    assert "generate_script" in tasks
    assert all(row["status"] == "success" for row in rows)


def test_empty_prompt_rejected(client: TestClient) -> None:
    r = client.post("/api/ai/test/text", json={"prompt": ""})
    assert r.status_code == 422