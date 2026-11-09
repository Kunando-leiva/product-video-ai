"""Lógica de negocio de carga y borrado de media."""
import logging
from pathlib import Path
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import NotFoundError, ValidationError
from app.core.media_types import classify
from app.core.paths import project_dir, sanitize_filename
from app.models.db_models import Media
from app.models.media import MediaRead
from app.repositories.media_repo import MediaRepository
from app.services.project_service import ProjectService
from app.services import media_analyzer  # ⬅️ nuevo


log = logging.getLogger("app.services.media")


MAX_FILE_SIZE = 500 * 1024 * 1024


class MediaService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = MediaRepository(session)
        self.projects = ProjectService(session)

    async def list_media(self, project_id: str) -> list[MediaRead]:
        await self.projects.get_project(project_id)
        items = await self.repo.list_by_project(project_id)
        return [self._to_read(m) for m in items]

    async def upload(
        self,
        project_id: str,
        original_name: str,
        content_type: str | None,
        data: bytes,
    ) -> MediaRead:
        await self.projects.get_project(project_id)

        if len(data) == 0:
            raise ValidationError(
                message="El archivo está vacío.",
                cause=original_name,
                solution="Elegí otro archivo.",
            )
        if len(data) > MAX_FILE_SIZE:
            raise ValidationError(
                message=f"El archivo supera el tamaño máximo ({MAX_FILE_SIZE // (1024*1024)} MB).",
                cause=f"{len(data)} bytes",
                solution="Comprimí el archivo o subí uno más chico.",
            )

        try:
            kind = classify(original_name, content_type)
        except ValueError as e:
            raise ValidationError(
                message="Tipo de archivo no soportado.",
                cause=str(e),
                solution="Usá imágenes JPG/PNG/WEBP, videos MP4/MOV/WEBM o audio MP3/WAV/M4A.",
            )

        safe_name = sanitize_filename(original_name)
        media_id = f"media_{uuid4().hex[:12]}"
        ext = Path(safe_name).suffix.lower() or ".bin"
        stored_name = f"{media_id}{ext}"

        project_root = project_dir(project_id)
        media_dir = project_root / "media"
        media_dir.mkdir(parents=True, exist_ok=True)
        file_path = media_dir / stored_name

        try:
            file_path.write_bytes(data)
        except OSError as e:
            raise ValidationError(
                message="No se pudo guardar el archivo en disco.",
                cause=str(e),
                solution="Verificá permisos y espacio libre.",
            )

        media = Media(
            id=media_id,
            project_id=project_id,
            type=kind,
            filename=stored_name,
            original_name=safe_name,
            path=str(file_path),
            metadata_json={"size_bytes": len(data), "content_type": content_type},
        )

        # ⬇️ Análisis (Regla 65) — modo degradado si no hay FFmpeg
        if kind in ("image", "video"):
            media_analyzer.analyze(media)
        if kind == "video":
            media_analyzer.generate_thumbnail(media)

        created = await self.repo.create(media)
        log.info(
            "Media subida: %s (%s, %d bytes) → %s",
            created.id, created.type, len(data), file_path,
        )
        return self._to_read(created)

    async def reanalyze(self, project_id: str, media_id: str) -> MediaRead:
        """Re-ejecuta el análisis (útil si FFmpeg se instaló después)."""
        await self.projects.get_project(project_id)
        media = await self.repo.get(media_id)
        if media is None or media.project_id != project_id:
            raise NotFoundError(message=f"No existe el archivo “{media_id}”.")

        if media.type in ("image", "video"):
            media_analyzer.analyze(media)
        if media.type == "video":
            media_analyzer.generate_thumbnail(media)

        updated = await self.repo.create(media)  # commit + refresh
        return self._to_read(updated)

    async def delete_media(self, project_id: str, media_id: str) -> None:
        await self.projects.get_project(project_id)
        media = await self.repo.get(media_id)
        if media is None or media.project_id != project_id:
            raise NotFoundError(message=f"No existe el archivo “{media_id}”.")

        for p in (media.path, media.thumbnail_path):
            if not p:
                continue
            fp = Path(p)
            if fp.exists():
                try:
                    fp.unlink()
                except OSError as e:
                    log.warning("No se pudo borrar %s: %s", fp, e)

        await self.repo.delete(media)
        log.info("Media eliminada: %s", media_id)

    def _to_read(self, m: Media) -> MediaRead:
        rel = Path(m.path).resolve().relative_to(settings.BASE_DIR.resolve())
        url = "/" + str(rel).replace("\\", "/")

        thumb_url = None
        if m.thumbnail_path:
            tp = Path(m.thumbnail_path).resolve()
            if tp.exists():
                thumb_url = "/" + str(
                    tp.relative_to(settings.BASE_DIR.resolve())
                ).replace("\\", "/")

        return MediaRead(
            id=m.id,
            project_id=m.project_id,
            type=m.type,
            filename=m.filename,
            original_name=m.original_name,
            path=m.path,
            url=url,
            duration=m.duration,
            width=m.width,
            height=m.height,
            fps=m.fps,
            orientation=m.orientation,
            thumbnail_path=m.thumbnail_path,
            thumbnail_url=thumb_url,
            created_at=m.created_at,
        )