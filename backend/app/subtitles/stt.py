"""Speech-to-Text con faster-whisper.

Modelo cargado perezosamente (lazy) para no bloquear el arranque.
"""
import logging
import threading
from pathlib import Path
from typing import Optional

from app.core.errors import NotReadyError, ValidationError
from app.subtitles.srt import SubtitleSegment


log = logging.getLogger("app.subtitles.stt")


_model = None
_model_lock = threading.Lock()
_loaded_model_name: Optional[str] = None


def is_available() -> bool:
    try:
        import faster_whisper  # noqa: F401
        return True
    except ImportError:
        return False


def _load_model(model_name: str):
    """Carga el modelo una sola vez (thread-safe)."""
    global _model, _loaded_model_name
    with _model_lock:
        if _model is not None and _loaded_model_name == model_name:
            return _model
        try:
            from faster_whisper import WhisperModel
        except ImportError as e:
            raise NotReadyError(
                message="El motor de subtítulos no está instalado.",
                cause=str(e),
                solution=(
                    "Instalá faster-whisper: "
                    "pip install faster-whisper  "
                    "(ver guía en el README del backend)."
                ),
            )
        log.info("Cargando modelo Whisper '%s' (puede tardar la primera vez)…", model_name)
        _model = WhisperModel(model_name, device="cpu", compute_type="int8")
        _loaded_model_name = model_name
        log.info("Modelo Whisper '%s' listo.", model_name)
        return _model


def transcribe(
    audio_path: Path,
    model_name: str = "small",
    language: Optional[str] = None,
) -> list[SubtitleSegment]:
    """Transcribe un archivo de audio y devuelve segmentos.

    Regla 86: language autodetectable; si se pasa 'es' fuerza español.
    """
    if not is_available():
        raise NotReadyError(
            message="El motor de subtítulos no está instalado.",
            solution=(
                "Ejecutá: pip install faster-whisper  "
                "y reiniciá el backend."
            ),
        )
    if not audio_path.exists():
        raise ValidationError(
            message="El archivo de audio no existe.",
            cause=str(audio_path),
        )

    model = _load_model(model_name)

    try:
        segments_iter, info = model.transcribe(
            str(audio_path),
            language=language,
            beam_size=5,
            vad_filter=True,  # detecta voz y salta silencios
        )
    except Exception as e:
        raise ValidationError(
            message="No se pudo transcribir el audio.",
            cause=str(e),
            solution="Verificá que el archivo no esté corrupto o en un formato soportado.",
        )

    result: list[SubtitleSegment] = []
    for i, seg in enumerate(segments_iter, start=1):
        text = (seg.text or "").strip()
        if not text:
            continue
        result.append(
            SubtitleSegment(
                index=i,
                start=round(float(seg.start), 3),
                end=round(float(seg.end), 3),
                text=text,
            )
        )

    log.info(
        "Transcripción OK: %s → %d segmentos (lang=%s)",
        audio_path.name, len(result), getattr(info, "language", "?"),
    )
    return result