"""Lógica de negocio de la timeline."""
import logging
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, ValidationError
from app.models.db_models import TimelineItem
from app.models.timeline import (
    TimelineItemRead,
    TimelineItemWrite,
    TimelineRead,
)
from app.repositories.media_repo import MediaRepository
from app.repositories.timeline_repo import TimelineRepository
from app.services.project_service import ProjectService


log = logging.getLogger("app.services.timeline")


VALID_EFFECTS = {
    None, "none",
    "zoom_in", "zoom_out",
    "pan_left", "pan_right", "pan_up", "pan_down",
    "fade",
}


class TimelineService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = TimelineRepository(session)
        self.media_repo = MediaRepository(session)
        self.projects = ProjectService(session)

    async def get(self, project_id: str) -> TimelineRead:
        await self.projects.get_project(project_id)
        items = await self.repo.list_by_project(project_id)
        return TimelineRead(items=[self._to_read(i) for i in items])

    async def replace(
        self, project_id: str, payload: list[TimelineItemWrite]
    ) -> TimelineRead:
        project = await self.projects.get_project(project_id)

        if not payload:
            # Permitir vaciar la timeline
            await self.repo.replace_all(project_id, [])
            return TimelineRead(items=[])

        # Validar media existe y pertenece al proyecto
        valid_media_ids: set[str] = set()
        for w in payload:
            if not w.media_id:
                continue
            m = await self.media_repo.get(w.media_id)
            if m is None or m.project_id != project_id:
                raise NotFoundError(
                    message=f"El archivo “{w.media_id}” no pertenece a este proyecto.",
                    solution="Recargá el material del proyecto.",
                )
            valid_media_ids.add(w.media_id)

        # Validar duración total
        total = sum(w.duration for w in payload)
        if total > project.duration + 30:
            # Margen de 30s: la timeline puede exceder un poco el target,
            # pero no disparatadamente.
            raise ValidationError(
                message=(
                    f"La duración total de la timeline ({total:.1f}s) supera "
                    f"el objetivo del proyecto ({project.duration}s)."
                ),
                solution="Acortá las duraciones o ampliá la duración del proyecto.",
            )

        # Validar efectos
        for w in payload:
            eff = w.effect or "none"
            if eff not in VALID_EFFECTS:
                raise ValidationError(
                    message=f"Efecto desconocido: “{eff}”.",
                    solution=f"Usá uno de: {sorted(e for e in VALID_EFFECTS if e)}.",
                )

        # Construir items nuevos con order_index secuencial
        new_items: list[TimelineItem] = []
        for idx, w in enumerate(payload):
            new_items.append(
                TimelineItem(
                    id=f"tl_{uuid4().hex[:12]}",
                    project_id=project_id,
                    media_id=w.media_id,
                    order_index=idx,
                    start=w.start or 0.0,
                    duration=w.duration,
                    effect=(w.effect or "none"),
                    text=w.text,
                )
            )

        saved = await self.repo.replace_all(project_id, new_items)
        log.info(
            "Timeline reemplazada en %s: %d items", project_id, len(saved)
        )
        return TimelineRead(items=[self._to_read(i) for i in saved])

    def _to_read(self, i: TimelineItem) -> TimelineItemRead:
        return TimelineItemRead(
            id=i.id,
            project_id=i.project_id,
            media_id=i.media_id,
            order_index=i.order_index,
            start=i.start,
            duration=i.duration,
            effect=i.effect,
            text=i.text,
        )