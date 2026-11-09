"""Endpoints de prueba del FFmpegEngine (Módulo 7).

Exponen operaciones puntuales para validar el motor desde el frontend
o curl. No forman parte del flujo de producción (eso es el Módulo 9).
"""
import logging
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import ffmpeg
from app.core.errors import ValidationError
from app.core.paths import project_dir
from app.db.session import get_session
from app.services.project_service import ProjectService
from app.video.engine import FFmpegEngine
from app.video.plan import VideoPlan


log = logging.getLogger("app.api.engine")
router = APIRouter(prefix="/projects/{project_id}/engine", tags=["engine"])


def _projects(session: AsyncSession = Depends(get_session)) -> ProjectService:
    return ProjectService(session)


class EngineStatus(BaseModel):
    ffmpeg_available: bool
    ffmpeg_path: str | None
    ffprobe_path: str | None
    version: str | None


class TestRequest(BaseModel):
    """Prueba una operación específica usando archivos ya cargados."""

    operation: str
    media_ids: list[str] = []
    options: dict = {}


class TestResponse(BaseModel):
    out_path: str
    duration: float | None
    size_bytes: int


@router.get("/status", response_model=EngineStatus)
async def engine_status() -> EngineStatus:
    path = ffmpeg.ffmpeg_path()
    version = None
    if path:
        try:
            info = ffmpeg._run([path, "-version"], timeout=5)
            first = (info.stdout or "").splitlines()[0] if info.stdout else None
            version = first
        except Exception:
            version = None
    return EngineStatus(
        ffmpeg_available=ffmpeg.is_available(),
        ffmpeg_path=path,
        ffprobe_path=ffmpeg.ffprobe_path(),
        version=version,
    )


@router.post("/test", response_model=TestResponse)
async def engine_test(
    project_id: str,
    payload: TestRequest,
    projects: ProjectService = Depends(_projects),
) -> TestResponse:
    """Ejecuta una operación puntual sobre el primer media disponible.

    Pensado para validar el motor durante el desarrollo.
    """
    ffmpeg.require_ffmpeg()
    await projects.get_project(project_id)

    # Recolectamos rutas de los media solicitados
    from app.repositories.media_repo import MediaRepository

    session = projects.repo.session
    media_repo = MediaRepository(session)

    items = []
    for mid in payload.media_ids:
        m = await media_repo.get(mid)
        if m is None or m.project_id != project_id:
            raise ValidationError(
                message=f"Media no encontrado: {mid}",
            )
        items.append(m)

    if not items and payload.operation != "image_to_video":
        raise ValidationError(
            message="Se requiere al menos un media para esta operación.",
        )

    out_dir = project_dir(project_id) / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_name = f"test_{uuid4().hex[:8]}.mp4"
    out_path = out_dir / out_name

    engine = FFmpegEngine()
    op = payload.operation

    if op == "image_to_video":
        opts = payload.options
        engine.image_to_video(
            image_path=items[0].path,
            out_path=str(out_path),
            duration=float(opts.get("duration", 3.0)),
            width=int(opts.get("width", 1080)),
            height=int(opts.get("height", 1920)),
            fps=int(opts.get("fps", 30)),
            fit=opts.get("fit", "cover"),
        )
    elif op == "trim_video":
        opts = payload.options
        engine.trim_video(
            in_path=items[0].path,
            out_path=str(out_path),
            start=float(opts.get("start", 0)),
            duration=float(opts.get("duration", 2)),
        )
    elif op == "concat_videos":
        if len(items) < 2:
            raise ValidationError(
                message="concat_videos necesita al menos 2 videos.",
            )
        engine.concat_videos([i.path for i in items], str(out_path))
    elif op == "merge_audio":
        if len(items) < 2:
            raise ValidationError(
                message="merge_audio necesita un video y un audio.",
            )
        opts = payload.options
        engine.merge_audio(
            video_path=items[0].path,
            audio_path=items[1].path,
            out_path=str(out_path),
            audio_volume=float(opts.get("audio_volume", 1.0)),
            video_volume=float(opts.get("video_volume", 0.0)),
            mix=bool(opts.get("mix", False)),
        )
    elif op == "overlay_text":
        opts = payload.options
        engine.overlay_text(
            in_path=items[0].path,
            out_path=str(out_path),
            text=opts.get("text", "HOLA"),
            position=opts.get("position", "bottom"),
            font_size=int(opts.get("font_size", 48)),
            color=opts.get("color", "white"),
        )
    elif op == "resize_and_pad":
        opts = payload.options
        engine.resize_and_pad(
            in_path=items[0].path,
            out_path=str(out_path),
            width=int(opts.get("width", 1080)),
            height=int(opts.get("height", 1920)),
            background=opts.get("background", "black"),
        )
    else:
        raise ValidationError(
            message=f"Operación no soportada: {op}",
            solution=(
                "Operaciones válidas: image_to_video, trim_video, "
                "concat_videos, merge_audio, overlay_text, resize_and_pad."
            ),
        )

    # Devolvemos info del resultado
    p = Path(out_path)
    if not p.exists():
        raise ValidationError(message="El motor no generó el archivo de salida.")

    return TestResponse(
        out_path=str(p),
        duration=ffmpeg.probe_duration(p),
        size_bytes=p.stat().st_size,
    )