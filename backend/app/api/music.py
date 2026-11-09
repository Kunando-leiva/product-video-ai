"""Endpoints de música."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.music import (
    MusicListResponse,
    MusicSelectionRequest,
    MusicSelectionResponse,
)
from app.services.music_service import MusicService


router = APIRouter(tags=["music"])


def _service(session: AsyncSession = Depends(get_session)) -> MusicService:
    return MusicService(session)


@router.get("/music/tracks", response_model=MusicListResponse)
async def list_tracks(
    service: MusicService = Depends(_service),
) -> MusicListResponse:
    return await service.list_tracks()


@router.get(
    "/projects/{project_id}/music",
    response_model=MusicSelectionResponse,
)
async def get_selection(
    project_id: str,
    service: MusicService = Depends(_service),
) -> MusicSelectionResponse:
    return await service.get_selection(project_id)


@router.put(
    "/projects/{project_id}/music",
    response_model=MusicSelectionResponse,
)
async def set_selection(
    project_id: str,
    payload: MusicSelectionRequest,
    service: MusicService = Depends(_service),
) -> MusicSelectionResponse:
    return await service.set_selection(project_id, payload)