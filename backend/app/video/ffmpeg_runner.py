"""Runner de FFmpeg: ejecución sin shell, con timeout y captura de stderr."""
import logging
import subprocess
from pathlib import Path

from app.core import ffmpeg
from app.core.errors import ValidationError


log = logging.getLogger("app.video.runner")


DEFAULT_TIMEOUT = 300


def run_ffmpeg(args: list[str], timeout: int = DEFAULT_TIMEOUT) -> None:
    ffmpeg.require_ffmpeg()
    binary = ffmpeg.ffmpeg_path() or "ffmpeg"

    full = [binary, "-nostdin", "-hide_banner", "-loglevel", "error", *args]
    log.debug("ffmpeg: %s", " ".join(full))

    try:
        result = subprocess.run(
            full,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        raise ValidationError(
            message=f"FFmpeg excedió el tiempo máximo ({timeout}s).",
            cause=str(e),
            solution="Probá con archivos más pequeños o recortá el video.",
        ) from e

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        log.error("FFmpeg stderr completo:\n%s", stderr)
        lines = stderr.splitlines()
        tail = "\n".join(lines[-20:]) if lines else f"exit code {result.returncode}"
        raise ValidationError(
            message="FFmpeg falló al procesar el video.",
            cause=tail,
            solution="Verificá los archivos de entrada o revisá los logs.",
        )


def ensure_parent(path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p