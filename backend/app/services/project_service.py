"""Lógica de negocio de proyectos."""
import logging
import shutil

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, ValidationError
from app.core.paths import project_dir
from app.models.db_models import Project
from app.models.project import (
    DURATIONS,
    FORMATS,
    ProjectCreate,
    ProjectUpdate,
)
from app.repositories.project_repo import ProjectRepository
from app.core.config import settings


log = logging.getLogger("app.services.projects")


class ProjectService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = ProjectRepository(session)

    async def list_projects(self) -> list[Project]:
        return list(await self.repo.list())

    async def get_project(self, project_id: str) -> Project:
        project = await self.repo.get(project_id)
        if project is None:
            raise NotFoundError(
                message=f"No existe el proyecto “{project_id}”.",
                solution="Volvé al listado y elegí un proyecto existente.",
            )
        return project

    async def create_project(self, data: ProjectCreate) -> Project:
        if data.format not in FORMATS:
            raise ValidationError(
                message=f"Formato inválido: {data.format}.",
                solution=f"Elegí uno de: {', '.join(FORMATS)}.",
            )
        if data.duration not in DURATIONS:
            raise ValidationError(
                message=f"Duración inválida: {data.duration}s.",
                solution=f"Elegí una de: {', '.join(map(str, DURATIONS))}s.",
            )

        from uuid import uuid4

        project_id = f"project_{uuid4().hex[:12]}"
        project = Project(
            id=project_id,
            name=data.name.strip(),
            product_name=data.name.strip(),
            product_url=data.product_url.strip(),
            format=data.format,
            duration=data.duration,
        )
        created = await self.repo.create(project)

        # Crear estructura en disco (Regla 8)
        root = project_dir(project_id)
        for sub in ("media", "audio", "subtitles", "generated", "renders", "thumbnails"):
            (root / sub).mkdir(parents=True, exist_ok=True)

        log.info("Proyecto creado: %s (%s)", created.id, created.name)
        return created

    async def update_project(
        self, project_id: str, data: ProjectUpdate
    ) -> Project:
        project = await self.get_project(project_id)
        changes = data.model_dump(exclude_unset=True)

        if "format" in changes and changes["format"] not in FORMATS:
            raise ValidationError(
                message=f"Formato inválido: {changes['format']}.",
                solution=f"Elegí uno de: {', '.join(FORMATS)}.",
            )
        if "duration" in changes and changes["duration"] not in DURATIONS:
            raise ValidationError(
                message=f"Duración inválida: {changes['duration']}s.",
            )

        for key, value in changes.items():
            setattr(project, key, value)

        updated = await self.repo.update(project)
        log.info("Proyecto actualizado: %s", project_id)
        return updated

    async def delete_project(self, project_id: str) -> None:
        project = await self.get_project(project_id)
        await self.repo.delete(project)

        # Borrar carpeta del proyecto (si existe)
        root = project_dir(project_id)
        if root.exists():
            try:
                shutil.rmtree(root)
            except OSError as e:
                log.warning("No se pudo borrar %s: %s", root, e)

        log.info("Proyecto eliminado: %s", project_id)