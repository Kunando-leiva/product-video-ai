"""Endpoints de subtítulos."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.render import RenderJobRead
from app.models.subtitles import (
    BurnRequest,
    SubtitleRead,
    SubtitleUpdate,
    TranscribeRequest,
    TranscribeResponse,
)
from app.services.subtitle_service import SubtitleService


router = APIRouter(prefix="/projects/{project_id}/subtitles", tags=["subtitles"])


def _service(session: AsyncSession = Depends(get_session)) -> SubtitleService:
    return SubtitleService(session)


@router.get("", response_model=SubtitleRead)
async def get_subtitles(
    project_id: str,
    service: SubtitleService = Depends(_service),
) -> SubtitleRead:
    return await service.get(project_id)


@router.put("", response_model=SubtitleRead)
async def update_subtitles(
    project_id: str,
    payload: SubtitleUpdate,
    service: SubtitleService = Depends(_service),
) -> SubtitleRead:
    return await service.update(project_id, payload)


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(
    project_id: str,
    payload: TranscribeRequest,
    service: SubtitleService = Depends(_service),
) -> TranscribeResponse:
    return await service.transcribe(project_id, payload)


@router.post("/burn", response_model=RenderJobRead)
async def burn(
    project_id: str,
    payload: BurnRequest = BurnRequest(),
    service: SubtitleService = Depends(_service),
) -> RenderJobRead:
    return await service.burn(project_id, payload)