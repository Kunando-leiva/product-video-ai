"""TTS Router: elige proveedor según configuración y disponibilidad."""
import logging

from app.audio.tts_cloud import CloudTTS
from app.audio.tts_local import LocalPiperTTS
from app.audio.tts_provider import TextToSpeechProvider


log = logging.getLogger("app.audio.tts_router")


_PROVIDERS: dict[str, TextToSpeechProvider] = {
    "local": LocalPiperTTS(),
    "cloud": CloudTTS(),
}


def get_provider(name: str | None = None) -> TextToSpeechProvider:
    """Devuelve el proveedor solicitado o el local si está disponible.

    Regla 20: el orden puede ser configurable; aquí la prioridad es local.
    """
    if name and name in _PROVIDERS:
        p = _PROVIDERS[name]
        if p.is_available():
            return p
        log.warning("Proveedor '%s' no disponible; usando local", name)

    local = _PROVIDERS["local"]
    if local.is_available():
        return local

    # Devolvemos igual (fallará con mensaje amigable)
    return local