"""Catálogo de pistas de música locales."""
import logging
from dataclasses import dataclass
from pathlib import Path

from app.core import ffmpeg
from app.core.config import settings


log = logging.getLogger("app.audio.music")


SUPPORTED_EXTS = {".mp3", ".m4a", ".aac", ".wav", ".ogg", ".flac"}


@dataclass
class MusicTrack:
    id: str           # nombre de archivo sin extensión
    name: str         # nombre legible
    filename: str
    path: Path
    duration: float | None
    size_bytes: int


def music_dir() -> Path:
    d = settings.MUSIC_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def list_tracks() -> list[MusicTrack]:
    """Lista pistas con metadata. Lee duración si FFmpeg está."""
    root = music_dir()
    tracks: list[MusicTrack] = []

    for f in sorted(root.iterdir()):
        if not f.is_file() or f.suffix.lower() not in SUPPORTED_EXTS:
            continue

        duration = None
        if ffmpeg.is_available():
            try:
                duration = ffmpeg.probe_duration(f)
            except Exception:
                duration = None

        tracks.append(
            MusicTrack(
                id=f.stem,
                name=f.stem.replace("_", " ").replace("-", " ").title(),
                filename=f.name,
                path=f,
                duration=duration,
                size_bytes=f.stat().st_size,
            )
        )
    return tracks


def find_track(track_id: str) -> MusicTrack:
    from app.core.errors import NotFoundError

    for t in list_tracks():
        if t.id == track_id or t.filename == track_id:
            return t
    raise NotFoundError(
        message=f"No existe la pista de música “{track_id}”.",
        solution=(
            "Copiá archivos MP3/WAV/M4A a assets/music/ y recargá la lista."
        ),
    )