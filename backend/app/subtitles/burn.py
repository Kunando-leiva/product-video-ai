"""Incrustar subtítulos SRT en un video con FFmpeg.

Se usa el filtro `subtitles` de FFmpeg. El estilo se controla por
`force_style` para que sea legible en móviles (Regla 93).
"""
import logging
from pathlib import Path

from app.core.errors import ValidationError
from app.video.ffmpeg_runner import ensure_parent, run_ffmpeg


log = logging.getLogger("app.subtitles.burn")


# Estilo moderno y legible (Regla 93: texto legible, subtítulos dentro de pantalla)
DEFAULT_STYLE = (
    "FontName=Arial,"
    "FontSize=22,"
    "PrimaryColour=&H00FFFFFF,"   # blanco (AABBGGRR)
    "OutlineColour=&H80000000,"   # contorno negro semi
    "BorderStyle=1,"
    "Outline=2,"
    "Shadow=0,"
    "Alignment=2,"                # centrado abajo
    "MarginV=60"
)


def burn_subtitles(
    video_path: Path,
    srt_path: Path,
    out_path: Path,
    style: str | None = None,
) -> Path:
    """Quema los subtítulos del SRT sobre el video.

    El archivo SRT debe estar en una ruta sin caracteres raros (escapamos).
    """
    if not video_path.exists():
        raise ValidationError(
            message="El video no existe.",
            cause=str(video_path),
        )
    if not srt_path.exists():
        raise ValidationError(
            message="El archivo de subtítulos no existe.",
            cause=str(srt_path),
        )

    style = style or DEFAULT_STYLE
    # Escapado de path para filtro subtitles (necesita / y escapar :)
    srt_escaped = (
        str(srt_path.resolve())
        .replace("\\", "/")
        .replace(":", "\\:")
    )
    style_escaped = style.replace("'", "\\'")

    vf = f"subtitles='{srt_escaped}':force_style='{style_escaped}'"

    out = ensure_parent(out_path)
    run_ffmpeg(
        [
            "-y",
            "-i", str(video_path),
            "-vf", vf,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-pix_fmt", "yuv420p",
            "-c:a", "copy",
            str(out),
        ],
        timeout=600,
    )
    log.info("Subtítulos incrustados: %s → %s", video_path.name, out.name)
    return out