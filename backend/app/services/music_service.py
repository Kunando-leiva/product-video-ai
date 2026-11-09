"""Lógica de negocio de música y voz (selección por proyecto)."""
import logging
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.audio.music import find_track, list_tracks
from app.core.config import settings
from app.core.errors import NotFoundError, ValidationError
from app.core.paths import project_dir, resolve_within
from app.models.music import (
    MusicListResponse,
    MusicSelectionRequest,
    MusicSelectionResponse,
    MusicTrackInfo,
)
from app.services.project_service import ProjectService


log = logging.getLogger("app.services.music")


class MusicService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.projects = ProjectService(session)

    # ------------------------------------------------------------------

    async def list_tracks(self) -> MusicListResponse:
        tracks = list_tracks()
        out: list[MusicTrackInfo] = []
        for t in tracks:
            rel = t.path.resolve().relative_to(settings.BASE_DIR.resolve())
            url = "/" + str(rel).replace("\\", "/")
            out.append(
                MusicTrackInfo(
                    id=t.id,
                    name=t.name,
                    filename=t.filename,
                    duration=t.duration,
                    size_bytes=t.size_bytes,
                    url=url,
                )
            )
        return MusicListResponse(tracks=out)

    # ------------------------------------------------------------------

    async def get_selection(self, project_id: str) -> MusicSelectionResponse:
        p = await self.projects.get_project(project_id)
        return MusicSelectionResponse(
            music_enabled=p.music_enabled,
            music_track=p.music_track,
            music_volume=p.music_volume,
            voice_enabled=p.voice_enabled,
            voice_track=p.voice_track,
        )

    async def set_selection(
        self, project_id: str, req: MusicSelectionRequest
    ) -> MusicSelectionResponse:
        p = await self.projects.get_project(project_id)

        if req.music_track is not None:
            if req.music_track == "":
                p.music_track = None
            else:
                # Valida que la pista exista
                find_track(req.music_track)
                p.music_track = req.music_track

        if req.music_enabled is not None:
            p.music_enabled = req.music_enabled
        if req.music_volume is not None:
            p.music_volume = req.music_volume

        if req.voice_track is not None:
            if req.voice_track == "":
                p.voice_track = None
            else:
                self._validate_voice_path(project_id, req.voice_track)
                p.voice_track = req.voice_track

        if req.voice_enabled is not None:
            p.voice_enabled = req.voice_enabled

        await self.projects.repo.update(p)
        log.info(
            "Audio actualizado en %s: voz=%s música=%s vol=%.2f",
            project_id, p.voice_track, p.music_track, p.music_volume,
        )
        return MusicSelectionResponse(
            music_enabled=p.music_enabled,
            music_track=p.music_track,
            music_volume=p.music_volume,
            voice_enabled=p.voice_enabled,
            voice_track=p.voice_track,
        )

    def _validate_voice_path(self, project_id: str, rel: str) -> None:
        """El voice_track debe ser un archivo dentro del proyecto."""
        # Acepta "/projects/<id>/audio/voice_xxx.wav" o "projects/<id>/audio/..."
        clean = rel.lstrip("/")
        if clean.startswith("projects/"):
            full = settings.BASE_DIR / clean
        else:
            full = settings.BASE_DIR / "projects" / project_id / "audio" / Path(clean).name

        full = full.resolve()
        project_root = project_dir(project_id).resolve()
        try:
            full.relative_to(project_root)
        except ValueError:
            raise ValidationError(
                message="La voz seleccionada no pertenece a este proyecto.",
            )
        if not full.exists():
            raise NotFoundError(
                message="El archivo de voz seleccionado no existe.",
            )