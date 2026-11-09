"""Lógica de negocio del render.

Ejecuta en background para no bloquear el event loop:
FFmpeg es bloqueante, así que corremos el pipeline en un ThreadPoolExecutor.
Cada job escribe su progreso en SQLite y el frontend hace polling.
"""
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import ffmpeg
from app.core.config import settings
from app.core.errors import NotFoundError, ValidationError
from app.audio.music import find_track
from app.core.paths import project_dir
from app.db.session import SessionLocal
from app.models.db_models import Media, RenderJob, TimelineItem
from app.models.render import RenderJobRead
from app.repositories.media_repo import MediaRepository
from app.repositories.render_repo import RenderRepository
from app.repositories.timeline_repo import TimelineRepository
from app.services.project_service import ProjectService
from app.video.render_pipeline import RenderPipeline


log = logging.getLogger("app.services.render")


# Executor global (FFmpeg es bloqueante)
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="render")


class RenderService:
    def __init__(
        self,
        session: AsyncSession,
        session_factory=None,
    ) -> None:
        self.session = session
        self.repo = RenderRepository(session)
        self.projects = ProjectService(session)
        self._session_factory = session_factory or SessionLocal

    # ------------------------------------------------------------------
    # Lectura
    # ------------------------------------------------------------------

    async def list_jobs(self, project_id: str) -> list[RenderJobRead]:
        await self.projects.get_project(project_id)
        jobs = await self.repo.list_by_project(project_id)
        return [self._to_read(j) for j in jobs]

    async def get_job(self, project_id: str, job_id: str) -> RenderJobRead:
        await self.projects.get_project(project_id)
        job = await self.repo.get(job_id)
        if job is None or job.project_id != project_id:
            raise NotFoundError(
                message=f"No existe el trabajo de render “{job_id}”.",
            )
        return self._to_read(job)

    # ------------------------------------------------------------------
    # Iniciar render
    # ------------------------------------------------------------------

    async def start_render(
        self, project_id: str, fps: int = 30
    ):
        """Crea el job y devuelve (job_read, coroutine).

        El router ejecuta la coroutine como BackgroundTask, de modo que
        corre después de devolver la response (y funciona en TestClient).
        """
        ffmpeg.require_ffmpeg()
        project = await self.projects.get_project(project_id)

        # Validaciones previas
        timeline_repo = TimelineRepository(self.session)
        items = list(await timeline_repo.list_by_project(project_id))
        if not items:
            raise ValidationError(
                message="La timeline está vacía.",
                solution="Agregá clips a la timeline antes de renderizar.",
            )

        media_repo = MediaRepository(self.session)
        media_by_id: dict[str, Media] = {}
        for it in items:
            if not it.media_id:
                continue
            m = await media_repo.get(it.media_id)
            if m is None:
                raise ValidationError(
                    message="Hay clips sin archivo asociado.",
                    solution="Recargá el material del proyecto.",
                )
            media_by_id[it.media_id] = m

        # Crear job
        job_id = f"job_{uuid4().hex[:12]}"
        out_dir = project_dir(project_id) / "renders"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_name = f"{job_id}.mp4"
        out_path = out_dir / out_name

        job = RenderJob(
            id=job_id,
            project_id=project_id,
            status="queued",
            progress=0.0,
            output_path=None,
        )
        await self.repo.add(job)
        log.info("Render encolado: %s (proyecto %s)", job_id, project_id)

        # Devolver (lectura, coroutine) — el router la correrá como BackgroundTask
        coro = self._run_job(
            job_id=job_id,
            project_id=project_id,
            timeline=items,
            media_by_id=media_by_id,
            out_path=out_path,
            fmt=project.format,
            fps=fps,
        )

        return self._to_read(job), coro

    async def delete_job(self, project_id: str, job_id: str) -> None:
        await self.projects.get_project(project_id)
        job = await self.repo.get(job_id)
        if job is None or job.project_id != project_id:
            raise NotFoundError(message=f"No existe el job “{job_id}”.")
        if job.output_path:
            p = Path(job.output_path)
            if p.exists():
                try:
                    p.unlink()
                except OSError:
                    pass
        await self.repo.delete(job)

    # ------------------------------------------------------------------
    # Ejecución en background
    # ------------------------------------------------------------------

    async def _run_job(
        self,
        job_id: str,
        project_id: str,
        timeline: list[TimelineItem],
        media_by_id: dict[str, Media],
        out_path: Path,
        fmt: str,
        fps: int,
    ) -> None:
        """Ejecuta el pipeline en un thread aparte y refleja progreso en DB."""
        try:
            # Marcar processing
            async with self._session_factory() as s:
                repo = RenderRepository(s)
                job = await repo.get(job_id)
                if job is None:
                    log.warning(
                        "Job %s no encontrado en la DB al iniciar", job_id
                    )
                    return
                job.status = "processing"
                job.progress = 0.0
                await repo.commit()

            # Resolver rutas de audio del proyecto (voz + música)
            voice_path, music_path, voice_volume, music_volume = (
                await self._resolve_audio(project_id)
            )

            # Progreso: cada llamada crea una sesión corta (para no bloquear)
            loop = asyncio.get_running_loop()

            def on_progress(p: float) -> None:
                # Callback viene del thread; schedule en el loop
                asyncio.run_coroutine_threadsafe(
                    self._update_progress(job_id, p), loop
                )

            work_dir = settings.TEMP_DIR / f"render_{job_id}"
            pipeline = RenderPipeline(
                work_dir=work_dir,
                output_path=out_path,
                fmt=fmt,
                fps=fps,
                voice_path=voice_path,
                music_path=music_path,
                voice_volume=voice_volume,
                music_volume=music_volume,
                on_progress=on_progress,
            )

            # Ejecutar pipeline en thread (bloqueante)
            await loop.run_in_executor(
                _executor,
                pipeline.render,
                timeline,
                media_by_id,
            )

            # Completed
            async with self._session_factory() as s:
                repo = RenderRepository(s)
                job = await repo.get(job_id)
                if job is None:
                    return
                job.status = "completed"
                job.progress = 1.0
                job.output_path = str(out_path)
                job.error = None
                await repo.commit()
            log.info("Render completado: %s → %s", job_id, out_path)

        except Exception as e:
            log.exception("Render falló: %s", job_id)
            try:
                async with self._session_factory() as s:
                    repo = RenderRepository(s)
                    job = await repo.get(job_id)
                    if job is None:
                        return
                    job.status = "failed"
                    job.error = f"{type(e).__name__}: {e}"
                    await repo.commit()
            except Exception:
                log.exception(
                    "No se pudo marcar el job %s como failed", job_id
                )

    # ------------------------------------------------------------------
    # Resolución de audio del proyecto
    # ------------------------------------------------------------------

    async def _resolve_audio(
        self, project_id: str
    ) -> tuple[Path | None, Path | None, float, float]:
        """Devuelve (voice_path, music_path, voice_volume, music_volume).

        Degrada silenciosamente: si un archivo no existe o la pista no
        está en el catálogo, se ignora (se renderiza sin ese audio).
        """
        voice_path: Path | None = None
        music_path: Path | None = None
        voice_volume: float = 1.0   # Regla 17: voz siempre al 100%
        music_volume: float = 0.15  # Regla 17: música 10–20% por defecto

        async with self._session_factory() as s:
            proj_service = ProjectService(s)
            proj = await proj_service.get_project(project_id)

            # --- Voz ---
            if proj.voice_enabled and proj.voice_track:
                vp = self._resolve_voice_path(project_id, proj.voice_track)
                if vp is not None and vp.exists():
                    voice_path = vp
                else:
                    log.warning(
                        "Voz configurada pero no encontrada: %s (proyecto %s)",
                        proj.voice_track, project_id,
                    )

            # voice_volume es un campo del modelo. Si no existe en tu
            # versión de db_models.py todavía, esta línea romperá con
            # AttributeError → Pylance te avisa. Agregalo al modelo
            # o eliminá el bloque.
            voice_volume = float(proj.voice_volume)

            # --- Música ---
            if proj.music_enabled and proj.music_track:
                try:
                    mt = find_track(proj.music_track)
                    music_path = mt.path
                    music_volume = float(proj.music_volume)
                except Exception:
                    log.warning(
                        "Pista de música no encontrada: %s (proyecto %s)",
                        proj.music_track, project_id,
                    )
                    music_path = None

        return voice_path, music_path, voice_volume, music_volume

    def _resolve_voice_path(
        self, project_id: str, rel: str
    ) -> Path | None:
        """Resuelve el voice_track a un Path absoluto dentro del proyecto.

        Acepta formatos:
          - "/projects/<id>/audio/voice_xxx.wav"  (URL relativa a BASE_DIR)
          - "projects/<id>/audio/voice_xxx.wav"
          - "voice_xxx.wav"                        (asume audio/ del proyecto)
          - "/abs/path/to/voice.wav"               (absoluto, se respeta)
        """
        if not rel:
            return None

        raw = Path(rel)

        # Absoluto: respetar tal cual
        if raw.is_absolute() and not rel.startswith("/projects/"):
            return raw

        # URL relativa estilo "/projects/<id>/audio/xxx.wav"
        clean = rel.lstrip("/")
        if clean.startswith("projects/"):
            return settings.BASE_DIR / clean

        # Nombre suelto → asumimos audio/ del proyecto
        return project_dir(project_id) / "audio" / raw.name

    async def _update_progress(self, job_id: str, progress: float) -> None:
        async with self._session_factory() as s:
            repo = RenderRepository(s)
            job = await repo.get(job_id)
            if job is None or job.status != "processing":
                return
            job.progress = progress
            await repo.commit()

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    def _to_read(self, j: RenderJob) -> RenderJobRead:
        url = None
        if j.output_path:
            p = Path(j.output_path)
            if p.exists():
                try:
                    rel = p.resolve().relative_to(settings.BASE_DIR.resolve())
                    url = "/" + str(rel).replace("\\", "/")
                except ValueError:
                    url = None

        return RenderJobRead(
            id=j.id,
            project_id=j.project_id,
            status=j.status,
            progress=j.progress,
            output_path=j.output_path,
            output_url=url,
            error=j.error,
            created_at=j.created_at,
            updated_at=j.updated_at,
        )