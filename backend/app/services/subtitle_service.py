"""Lógica de negocio de subtítulos."""
import logging
import shutil
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import ffmpeg
from app.core.errors import NotFoundError, ValidationError
from app.core.paths import project_dir
from app.models.render import RenderJobRead
from app.models.subtitles import (
    BurnRequest,
    SegmentModel,
    SubtitleRead,
    SubtitleUpdate,
    TranscribeRequest,
    TranscribeResponse,
)
from app.repositories.media_repo import MediaRepository
from app.repositories.render_repo import RenderRepository
from app.services.project_service import ProjectService
from app.subtitles import burn as burn_mod
from app.subtitles import stt
from app.subtitles.srt import (
    SubtitleSegment,
    segments_to_srt,
    srt_to_segments,
)
from app.video.ffmpeg_runner import run_ffmpeg  # noqa: F401  (por si se usa)


log = logging.getLogger("app.services.subtitles")


SRT_NAME = "subtitles.srt"
BURNED_NAME = "with_subtitles.mp4"


class SubtitleService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.projects = ProjectService(session)
        self.media = MediaRepository(session)
        self.renders = RenderRepository(session)

    # ------------------------------------------------------------------
    # Lectura / escritura
    # ------------------------------------------------------------------

    async def get(self, project_id: str) -> SubtitleRead:
        await self.projects.get_project(project_id)
        path = project_dir(project_id) / "subtitles" / SRT_NAME
        if not path.exists():
            return SubtitleRead(exists=False, segments=[])
        srt = path.read_text(encoding="utf-8")
        segs = srt_to_segments(srt)
        return SubtitleRead(
            exists=True,
            srt=srt,
            segments=[
                SegmentModel(start=s.start, end=s.end, text=s.text) for s in segs
            ],
        )

    async def update(
        self, project_id: str, payload: SubtitleUpdate
    ) -> SubtitleRead:
        await self.projects.get_project(project_id)
        if not payload.segments:
            raise ValidationError(
                message="No hay segmentos para guardar.",
            )
        segs = [
            SubtitleSegment(index=i + 1, start=s.start, end=s.end, text=s.text)
            for i, s in enumerate(payload.segments)
        ]
        # Ordenar por start por si el frontend los mezcla
        segs.sort(key=lambda s: s.start)
        for i, s in enumerate(segs, start=1):
            s.index = i

        srt = segments_to_srt(segs)
        sub_dir = project_dir(project_id) / "subtitles"
        sub_dir.mkdir(parents=True, exist_ok=True)
        (sub_dir / SRT_NAME).write_text(srt, encoding="utf-8")
        log.info("Subtítulos guardados para %s (%d segmentos)", project_id, len(segs))
        return SubtitleRead(
            exists=True,
            srt=srt,
            segments=[
                SegmentModel(start=s.start, end=s.end, text=s.text) for s in segs
            ],
        )

    # ------------------------------------------------------------------
    # Transcripción
    # ------------------------------------------------------------------

    async def transcribe(
        self, project_id: str, req: TranscribeRequest
    ) -> TranscribeResponse:
        await self.projects.get_project(project_id)

        m = await self.media.get(req.media_id)
        if m is None or m.project_id != project_id:
            raise NotFoundError(
                message=f"Media no encontrado: {req.media_id}",
            )
        if m.type not in ("audio", "video"):
            raise ValidationError(
                message="Solo se pueden transcribir archivos de audio o video.",
            )

        media_path = Path(m.path)
        if not media_path.exists():
            raise ValidationError(
                message="El archivo de media ya no existe en disco.",
                solution="Volvé a subirlo.",
            )

        # Si es video, extraemos el audio a WAV 16kHz mono (óptimo para Whisper)
        audio_for_stt = media_path
        temp_audio: Path | None = None
        if m.type == "video":
            ffmpeg.require_ffmpeg()
            temp_audio = project_dir(project_id) / "audio" / f"_stt_{m.id}.wav"
            temp_audio.parent.mkdir(parents=True, exist_ok=True)
            run_ffmpeg(
                [
                    "-y",
                    "-i", str(media_path),
                    "-vn",
                    "-ac", "1",
                    "-ar", "16000",
                    "-c:a", "pcm_s16le",
                    str(temp_audio),
                ],
                timeout=300,
            )
            audio_for_stt = temp_audio

        try:
            segs = stt.transcribe(
                audio_for_stt,
                model_name=req.model,
                language=req.language,
            )
        finally:
            if temp_audio and temp_audio.exists():
                try:
                    temp_audio.unlink()
                except OSError:
                    pass

        if not segs:
            raise ValidationError(
                message="No se detectó voz en el archivo.",
                solution="Verificá que el audio tenga voz clara y no solo música.",
            )

        srt = segments_to_srt(segs)
        sub_dir = project_dir(project_id) / "subtitles"
        sub_dir.mkdir(parents=True, exist_ok=True)
        (sub_dir / SRT_NAME).write_text(srt, encoding="utf-8")

        log.info("Transcripción guardada para %s (%d segmentos)", project_id, len(segs))
        return TranscribeResponse(
            segments=[
                SegmentModel(start=s.start, end=s.end, text=s.text) for s in segs
            ],
            srt=srt,
            language=req.language,
        )

    # ------------------------------------------------------------------
    # Incrustar subtítulos en el render
    # ------------------------------------------------------------------

    async def burn(
        self, project_id: str, req: BurnRequest
    ) -> RenderJobRead:
        """Aplica el SRT a un render ya completado y devuelve un nuevo job."""
        await self.projects.get_project(project_id)

        srt_path = project_dir(project_id) / "subtitles" / SRT_NAME
        if not srt_path.exists():
            raise ValidationError(
                message="No hay subtítulos para aplicar.",
                solution="Primero transcribí o cargá un SRT manualmente.",
            )

        # Encontrar el render a usar
        if req.render_job_id:
            job = await self.renders.get(req.render_job_id)
            if job is None or job.project_id != project_id:
                raise NotFoundError(message="Render no encontrado.")
        else:
            jobs = list(await self.renders.list_by_project(project_id))
            job = next((j for j in jobs if j.status == "completed"), None)
            if job is None:
                raise ValidationError(
                    message="No hay ningún render completado.",
                    solution="Renderizá el video primero (Módulo 9).",
                )

        if not job.output_path:
            raise ValidationError(message="El render no tiene archivo de salida.")

        video_path = Path(job.output_path)
        if not video_path.exists():
            raise ValidationError(
                message="El archivo del render ya no existe.",
                solution="Volvé a renderizar.",
            )

        # Copiar el video a renders/with_subtitles.mp4 (o sufijo por job)
        renders_dir = project_dir(project_id) / "renders"
        out_path = renders_dir / f"{job.id}_subtitled.mp4"

        ffmpeg.require_ffmpeg()
        burn_mod.burn_subtitles(video_path, srt_path, out_path)

        # Registrar como un nuevo job "completed"
        from uuid import uuid4
        from app.models.db_models import RenderJob

        new_id = f"job_{uuid4().hex[:12]}"
        new_job = RenderJob(
            id=new_id,
            project_id=project_id,
            status="completed",
            progress=1.0,
            output_path=str(out_path),
        )
        created = await self.renders.add(new_job)

        # Reutilizar el helper del RenderService para la URL
        from app.services.render_service import RenderService

        rs = RenderService(self.session)
        return rs._to_read(created)