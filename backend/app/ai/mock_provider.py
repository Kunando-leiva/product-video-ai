"""MockProvider: respuestas deterministas para tests y para desarrollo
cuando no hay ningún modelo real conectado (Módulo 14+).

Regla 72: la interfaz debe poder probarse sin IA real.
"""
import hashlib
import json
import logging
from typing import Optional

from app.ai.provider import (
    AIProvider,
    AIImageAnalysis,
    AIScriptRequest,
    AIScriptResponse,
    AIScriptSection,
    AITextRequest,
    AITextResponse,
    AIVideoAnalysis,
)


log = logging.getLogger("app.ai.mock")


class MockProvider(AIProvider):
    name = "mock"
    requires_internet = False
    default_model = "mock-1"

    def is_available(self) -> bool:
        return True  # siempre disponible

    # ------------------------------------------------------------------
    # Texto
    # ------------------------------------------------------------------

    async def generate_text(self, req: AITextRequest) -> AITextResponse:
        if req.json_schema:
            # Devuelve un JSON válido que respeta el esquema (estructura simple)
            payload = self._mock_json(req)
            text = json.dumps(payload, ensure_ascii=False)
        else:
            # Devuelve un texto derivado del prompt
            text = (
                f"[MOCK] Respuesta a: {req.prompt[:80]}"
                + ("…" if len(req.prompt) > 80 else "")
            )

        # Conteo de tokens "realista" (4 chars ≈ 1 token)
        tokens_in = max(1, len(req.prompt) // 4)
        tokens_out = max(1, len(text) // 4)
        return AITextResponse(
            text=text,
            model=self.default_model or "mock-1",
            provider=self.name,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
        )

    def _mock_json(self, req: AITextRequest) -> dict:
        """Genera un JSON que respeta `req.json_schema` (aproximado)."""
        schema = req.json_schema or {}
        return self._mock_from_schema(schema)

    def _mock_from_schema(self, schema: dict) -> dict:
        t = schema.get("type")
        if t == "object":
            out = {}
            for k, v in (schema.get("properties") or {}).items():
                out[k] = self._mock_from_schema(v)
            return out
        if t == "array":
            item = schema.get("items") or {"type": "string"}
            return [self._mock_from_schema(item)]
        if t == "integer":
            return 1
        if t == "number":
            return 1.0
        if t == "boolean":
            return True
        return "mock"

    # ------------------------------------------------------------------
    # Imagen
    # ------------------------------------------------------------------

    async def analyze_image(
        self, image_path: str, prompt: Optional[str] = None
    ) -> AIImageAnalysis:
        # Determinista en base a la ruta (útil para tests)
        h = hashlib.sha256(image_path.encode()).hexdigest()[:8]
        return AIImageAnalysis(
            description=f"[MOCK {h}] Imagen de producto detectada.",
            tags=["product", "mock"],
            is_product=True,
            quality_score=0.75,
            provider=self.name,
            model=self.default_model or "mock-1",
        )

    # ------------------------------------------------------------------
    # Video
    # ------------------------------------------------------------------

    async def analyze_video(
        self, video_path: str, prompt: Optional[str] = None
    ) -> AIVideoAnalysis:
        h = hashlib.sha256(video_path.encode()).hexdigest()[:8]
        return AIVideoAnalysis(
            description=f"[MOCK {h}] Video de producto detectado.",
            scenes=["escena 1", "escena 2", "escena 3"],
            tags=["product", "video", "mock"],
            quality_score=0.7,
            provider=self.name,
            model=self.default_model or "mock-1",
        )

    # ------------------------------------------------------------------
    # Guion
    # ------------------------------------------------------------------

    async def generate_script(self, req: AIScriptRequest) -> AIScriptResponse:
        # Distribuye la duración total entre hook / características / CTA
        total = float(req.duration)
        hook_d = round(total * 0.2, 1)
        cta_d = round(total * 0.15, 1)
        body_d = round(total - hook_d - cta_d, 1)

        hook = f"¿Buscás {req.product_name}?"
        cta = "Comprá ahora, link en la descripción."

        body_text = (
            req.product_description.strip()
            or f"{req.product_name} con calidad premium."
        )
        sections = [
            AIScriptSection(
                text=body_text,
                duration=body_d,
            )
        ]

        return AIScriptResponse(
            hook=hook,
            sections=sections,
            cta=cta,
            provider=self.name,
            model=self.default_model or "mock-1",
        )