"""Endpoints de voz."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.voice import (
    SynthesizeRequest,
    SynthesizeResponse,
    VoiceListResponse,
)
from app.services.voice_service import VoiceService


router = APIRouter(tags=["voice"])


def _service(session: AsyncSession = Depends(get_session)) -> VoiceService:
    return VoiceService(session)


@router.get("/voice/voices", response_model=VoiceListResponse)
async def list_voices(
    service: VoiceService = Depends(_service),
) -> VoiceListResponse:
    return await service.list_voices()


@router.post(
    "/projects/{project_id}/voice/synthesize",
    response_model=SynthesizeResponse,
)
async def synthesize(
    project_id: str,
    payload: SynthesizeRequest,
    service: VoiceService = Depends(_service),
) -> SynthesizeResponse:
    return await service.synthesize(project_id, payload)