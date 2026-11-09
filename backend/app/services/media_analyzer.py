"""Analiza archivos multimedia y completa la metadata de la tabla media."""
import logging
from pathlib import Path
from typing import Any, Optional

from app.core import ffmpeg
from app.models.db_models import Media


log = logging.getLogger("app.services.analyzer")


def _orientation(width: Optional[int], height: Optional[int]) -> Optional[str]:
    if not width or not height:
        return None
    if width == height:
        return "square"
    return "vertical" if height > width else "horizontal"


def _parse_fps(stream: dict[str, Any]) -> Optional[float]:
    """avg_frame_rate viene como '30000/1001' o '0/0'."""
    raw = stream.get("avg_frame_rate") or stream.get("r_frame_rate")
    if not raw or raw in ("0/0", "N/A"):
        return None
    try:
        num, den = raw.split("/")
        num_f, den_f = float(num), float(den)
        if den_f == 0:
            return None
        fps = num_f / den_f
        return round(fps, 3) if fps > 0 else None
    except (ValueError, ZeroDivisionError):
        return None


def analyze(media: Media) -> None:
    """Rellena metadata de un registro Media in-place.

    No hace commit: eso lo maneja el service que lo invoque.
    Si FFmpeg no está disponible, sale silenciosamente (modo degradado).
    """
    if not ffmpeg.is_available():
        log.info("FFmpeg no disponible; se omite análisis de %s", media.id)
        return

    path = Path(media.path)
    if not path.exists():
        log.warning("Archivo no encontrado: %s", path)
        return

    try:
        info = ffmpeg.probe(path)
    except Exception as e:
        log.warning("Análisis falló para %s: %s", media.id, e)
        return

    streams = info.get("streams") or []
    fmt = info.get("format") or {}

    video_stream = next(
        (s for s in streams if s.get("codec_type") == "video"), None
    )
    audio_stream = next(
        (s for s in streams if s.get("codec_type") == "audio"), None
    )

    # Duración (prioridad: format.duration; fallback: stream.duration)
    duration: Optional[float] = None
    for src in (fmt.get("duration"), (video_stream or {}).get("duration"),
                (audio_stream or {}).get("duration")):
        if src:
            try:
                duration = round(float(src), 3)
                break
            except (TypeError, ValueError):
                continue

    # Dimensiones: para imágenes/videos tomamos del stream de video
    width = height = None
    if video_stream:
        try:
            width = int(video_stream.get("width")) if video_stream.get("width") else None
            height = int(video_stream.get("height")) if video_stream.get("height") else None
        except (TypeError, ValueError):
            width = height = None

    # FPS: solo tiene sentido para videos. FFprobe reporta 25/1 por defecto
    # en el stream de video "falso" que genera para una imagen, así que
    # para imágenes lo forzamos a None.
    if media.type == "image":
        fps = None
    else:
        fps = _parse_fps(video_stream) if video_stream else None

    media.duration = duration
    media.width = width
    media.height = height
    media.fps = fps
    media.orientation = _orientation(width, height)

    # Enriquecer metadata_json sin pisar lo que ya haya
    existing = dict(media.metadata_json or {})
    existing.update(
        {
            "codec_video": (video_stream or {}).get("codec_name"),
            "codec_audio": (audio_stream or {}).get("codec_name"),
            "bit_rate": fmt.get("bit_rate"),
            "format_name": fmt.get("format_name"),
            "size_bytes": fmt.get("size"),
        }
    )
    media.metadata_json = existing

    log.info(
        "Analizado %s → %sx%s @ %sfps · %ss · %s",
        media.id, width, height, fps, duration, media.orientation,
    )


def generate_thumbnail(media: Media) -> bool:
    """Genera thumbnail para videos. Devuelve True si se creó."""
    if media.type != "video":
        return False
    if not ffmpeg.is_available():
        return False

    video_path = Path(media.path)
    thumb_dir = video_path.parent.parent / "thumbnails"
    thumb_path = thumb_dir / f"{media.id}.jpg"

    ok = ffmpeg.extract_thumbnail(video_path, thumb_path, at_seconds=1.0)
    if ok:
        media.thumbnail_path = str(thumb_path)
    return ok