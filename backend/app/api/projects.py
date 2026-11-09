"""Endpoints de proyectos (CRUD)."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.project import ProjectCreate, ProjectRead, ProjectUpdate
from app.services.project_service import ProjectService


router = APIRouter(prefix="/projects", tags=["projects"])


def _service(session: AsyncSession = Depends(get_session)) -> ProjectService:
    return ProjectService(session)


@router.get("", response_model=list[ProjectRead])
async def list_projects(
    service: ProjectService = Depends(_service),
) -> list[ProjectRead]:
    projects = await service.list_projects()
    return [ProjectRead.model_validate(p) for p in projects]


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    service: ProjectService = Depends(_service),
) -> ProjectRead:
    project = await service.create_project(payload)
    return ProjectRead.model_validate(project)


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(
    project_id: str,
    service: ProjectService = Depends(_service),
) -> ProjectRead:
    project = await service.get_project(project_id)
    return ProjectRead.model_validate(project)


@router.put("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: str,
    payload: ProjectUpdate,
    service: ProjectService = Depends(_service),
) -> ProjectRead:
    project = await service.update_project(project_id, payload)
    return ProjectRead.model_validate(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    service: ProjectService = Depends(_service),
) -> None:
    await service.delete_project(project_id)