"""Stub de TTS cloud (Regla 16).

La interfaz queda lista para que el Módulo 16 enchufe Grok/OpenAI/ElevenLabs.
"""
from pathlib import Path

from app.audio.tts_provider import TextToSpeechProvider
from app.core.errors import NotReadyError


class CloudTTS(TextToSpeechProvider):
    name = "cloud"

    def is_available(self) -> bool:
        return False

    def synthesize(
        self,
        text: str,
        out_path: Path,
        voice_id: str | None = None,
        speed: float = 1.0,
    ) -> Path:
        raise NotReadyError(
            message="El proveedor cloud de voz no está habilitado.",
            solution=(
                "Configurá una API key en Configuración → IA (Módulo 16)."
            ),
        )