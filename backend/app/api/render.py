"""Endpoints de render."""
import asyncio
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.session import get_session
from app.models.render import RenderJobRead, RenderStartRequest
from app.services.render_service import RenderService


router = APIRouter(prefix="/projects/{project_id}/render", tags=["render"])


def _get_session_factory() -> Optional[async_sessionmaker]:
    """Dependency inyectable.

    - En producción: devuelve None → RenderService usa SessionLocal.
    - En tests: se overridea para devolver `db_session.async_session`,
      así `_run_job` ve la MISMA DB que el endpoint que creó el job.
    """
    return None


def _service(
    session: AsyncSession = Depends(get_session),
    session_factory: Optional[async_sessionmaker] = Depends(_get_session_factory),
) -> RenderService:
    return RenderService(session, session_factory=session_factory)


@router.get("", response_model=list[RenderJobRead])
async def list_jobs(
    project_id: str,
    service: RenderService = Depends(_service),
) -> list[RenderJobRead]:
    return await service.list_jobs(project_id)


@router.post("", response_model=RenderJobRead, status_code=status.HTTP_202_ACCEPTED)
async def start_render(
    project_id: str,
    background: BackgroundTasks,
    payload: RenderStartRequest = RenderStartRequest(),
    service: RenderService = Depends(_service),
) -> RenderJobRead:
    job, coro = await service.start_render(project_id, fps=payload.fps)

    # Starlette ejecuta coroutines en el event loop correcto.
    # NO usar asyncio.run() — crearía un loop nuevo y rompería SQLAlchemy.
    async def _await_job() -> None:
        await coro

    background.add_task(_await_job)
    return job


@router.get("/{job_id}", response_model=RenderJobRead)
async def get_job(
    project_id: str,
    job_id: str,
    service: RenderService = Depends(_service),
) -> RenderJobRead:
    return await service.get_job(project_id, job_id)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    project_id: str,
    job_id: str,
    service: RenderService = Depends(_service),
) -> None:
    await service.delete_job(project_id, job_id)