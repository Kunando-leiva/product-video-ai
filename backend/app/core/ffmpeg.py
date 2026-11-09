"""Detección y ejecución segura de FFmpeg/FFprobe.

Regla 56: nunca ejecutar comandos provenientes de la IA o del usuario.
Solo se ejecutan comandos construidos por el backend con listas de args.
"""
import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any, Optional

from app.core.errors import ValidationError


log = logging.getLogger("app.ffmpeg")


def ffmpeg_path() -> Optional[str]:
    return shutil.which("ffmpeg")


def ffprobe_path() -> Optional[str]:
    return shutil.which("ffprobe")


def is_available() -> bool:
    return ffmpeg_path() is not None and ffprobe_path() is not None


def require_ffmpeg() -> None:
    if not is_available():
        raise ValidationError(
            message="FFmpeg no está instalado.",
            cause="No se encontraron los binarios 'ffmpeg' ni 'ffprobe' en el PATH.",
            solution=(
                "Instalá FFmpeg: Windows → https://www.gyan.dev/ffmpeg/builds/ · "
                "Linux → sudo apt install ffmpeg · macOS → brew install ffmpeg"
            ),
        )


def _run(args: list[str], timeout: int = 60) -> subprocess.CompletedProcess:
    """Ejecuta un comando sin shell, con timeout, capturando salida."""
    log.debug("run: %s", " ".join(args))
    try:
        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,  # Regla 56: nunca shell=True
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        raise ValidationError(
            message="La operación de video tardó demasiado.",
            cause=f"timeout={timeout}s",
            solution="Probá con un archivo más pequeño.",
        ) from e


def probe(path: Path) -> dict[str, Any]:
    """Devuelve el JSON completo de ffprobe para un archivo."""
    require_ffmpeg()
    result = _run(
        [
            ffprobe_path() or "ffprobe",
            "-v", "error",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(path),
        ],
        timeout=30,
    )
    if result.returncode != 0:
        raise ValidationError(
            message="No se pudo leer el archivo multimedia.",
            cause=result.stderr.strip() or f"exit={result.returncode}",
            solution="Verificá que el archivo no esté corrupto.",
        )
    try:
        return json.loads(result.stdout or "{}")
    except json.JSONDecodeError as e:
        raise ValidationError(
            message="Respuesta inválida de ffprobe.",
            cause=str(e),
        )


def extract_thumbnail(
    video_path: Path,
    out_path: Path,
    at_seconds: float = 1.0,
    width: int = 480,
) -> bool:
    """Extrae un frame del video como JPG. Devuelve True si tuvo éxito."""
    require_ffmpeg()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    result = _run(
        [
            ffmpeg_path() or "ffmpeg",
            "-y",
            "-ss", str(max(at_seconds, 0)),
            "-i", str(video_path),
            "-frames:v", "1",
            "-vf", f"scale={width}:-1",
            "-q:v", "3",
            str(out_path),
        ],
        timeout=60,
    )
    ok = result.returncode == 0 and out_path.exists()
    if not ok:
        log.warning("Thumbnail falló para %s: %s", video_path, result.stderr[-300:])
    return ok


def make_solid_image(out_path: Path, width: int, height: int, color: str = "purple") -> None:
    """Genera una imagen sólida (útil para tests o placeholders)."""
    require_ffmpeg()
    result = _run(
        [
            ffmpeg_path() or "ffmpeg",
            "-y",
            "-f", "lavfi",
            "-i", f"color=c={color}:s={width}x{height}:d=1",
            "-frames:v", "1",
            str(out_path),
        ],
        timeout=30,
    )
    if result.returncode != 0:
        raise ValidationError(
            message="No se pudo generar la imagen de prueba.",
            cause=result.stderr[-300:],
        )


def make_test_video(
    out_path: Path,
    seconds: float = 3.0,
    fps: int = 24,
    size: str = "320x240",
) -> None:
    """Genera un video de prueba (útil para tests)."""
    require_ffmpeg()
    result = _run(
        [
            ffmpeg_path() or "ffmpeg",
            "-y",
            "-f", "lavfi",
            "-i", f"testsrc=size={size}:rate={fps}:duration={seconds}",
            "-pix_fmt", "yuv420p",
            str(out_path),
        ],
        timeout=60,
    )
    if result.returncode != 0:
        raise ValidationError(
            message="No se pudo generar el video de prueba.",
            cause=result.stderr[-300:],
        )


def probe_duration(path: Path) -> Optional[float]:
    """Devuelve duración en segundos, o None si no se puede determinar."""
    try:
        info = probe(path)
    except Exception:
        return None
    fmt = info.get("format") or {}
    d = fmt.get("duration")
    if not d:
        return None
    try:
        return round(float(d), 3)
    except (TypeError, ValueError):
        return None


def make_test_audio(out_path: Path, seconds: float = 2.0) -> None:
    """Genera voz sintética de prueba con flite (WAV 16kHz mono).

    Requiere FFmpeg compilado con --enable-libflite.
    """
    require_ffmpeg()
    # frases de flite que duran aprox `seconds` segundos
    text = "hello world this is a test" if seconds <= 3 else "hello world this is a test of speech recognition"
    result = _run(
        [
            ffmpeg_path() or "ffmpeg",
            "-y",
            "-f", "lavfi",
            "-i", f"flite=text='{text}':voice=slt",
            "-ar", "16000",
            "-ac", "1",
            "-c:a", "pcm_s16le",
            str(out_path),
        ],
        timeout=30,
    )
    if result.returncode != 0:
        raise ValidationError(
            message="No se pudo generar el audio de prueba.",
            cause=result.stderr[-300:],
        )