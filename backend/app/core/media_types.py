"""Tipos de archivo permitidos y utilidades de clasificación."""
from pathlib import Path


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTS = {".mp4", ".mov", ".webm", ".mkv", ".m4v"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".ogg"}

ALL_EXTS = IMAGE_EXTS | VIDEO_EXTS | AUDIO_EXTS

# MIME permitidos (tolerante: muchos navegadores mandan octet-stream)
IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp"}
VIDEO_MIMES = {"video/mp4", "video/quicktime", "video/webm", "video/x-matroska"}
AUDIO_MIMES = {"audio/mpeg", "audio/wav", "audio/x-wav", "audio/mp4", "audio/aac", "audio/ogg"}

ALL_MIMES = IMAGE_MIMES | VIDEO_MIMES | AUDIO_MIMES


def classify(filename: str, content_type: str | None) -> str:
    """Devuelve 'image' | 'video' | 'audio'.

    Se prioriza la extensión (más confiable que content_type en multipart).
    Lanza ValueError si no se puede clasificar.
    """
    ext = Path(filename).suffix.lower()
    if ext in IMAGE_EXTS:
        return "image"
    if ext in VIDEO_EXTS:
        return "video"
    if ext in AUDIO_EXTS:
        return "audio"

    # Fallback por MIME
    mime = (content_type or "").lower()
    if mime in IMAGE_MIMES:
        return "image"
    if mime in VIDEO_MIMES:
        return "video"
    if mime in AUDIO_MIMES:
        return "audio"

    raise ValueError(f"Extensión o tipo no soportado: {filename!r} ({content_type!r})")


def is_allowed_extension(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALL_EXTS