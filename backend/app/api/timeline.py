"""Endpoints de la timeline por proyecto."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.timeline import TimelineRead, TimelineReplaceRequest
from app.services.timeline_service import TimelineService


router = APIRouter(prefix="/projects/{project_id}/timeline", tags=["timeline"])


def _service(session: AsyncSession = Depends(get_session)) -> TimelineService:
    return TimelineService(session)


@router.get("", response_model=TimelineRead)
async def get_timeline(
    project_id: str,
    service: TimelineService = Depends(_service),
) -> TimelineRead:
    return await service.get(project_id)


@router.put("", response_model=TimelineRead)
async def replace_timeline(
    project_id: str,
    payload: TimelineReplaceRequest,
    service: TimelineService = Depends(_service),
) -> TimelineRead:
    return await service.replace(project_id, payload.items)