"""Endpoints de IA."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.ai import (
    AIProviderInfo,
    AIProvidersResponse,
    AIScriptTestRequest,
    AIScriptTestResponse,
    AITextTestRequest,
    AITextTestResponse,
    AIUsageResponse,
)
from app.services.ai_service import AIService


router = APIRouter(prefix="/ai", tags=["ai"])


def _service(session: AsyncSession = Depends(get_session)) -> AIService:
    return AIService(session)


@router.get("/providers", response_model=AIProvidersResponse)
async def list_providers(
    service: AIService = Depends(_service),
) -> AIProvidersResponse:
    return await service.list_providers()


@router.get("/providers/{name}", response_model=AIProviderInfo)
async def provider_detail(
    name: str,
    service: AIService = Depends(_service),
) -> AIProviderInfo:
    return await service.provider_detail(name)


@router.post("/test/text", response_model=AITextTestResponse)
async def test_text(
    payload: AITextTestRequest,
    service: AIService = Depends(_service),
) -> AITextTestResponse:
    return await service.test_text(payload)


@router.post("/test/script", response_model=AIScriptTestResponse)
async def test_script(
    payload: AIScriptTestRequest,
    service: AIService = Depends(_service),
) -> AIScriptTestResponse:
    return await service.test_script(payload)


@router.get("/usage", response_model=AIUsageResponse)
async def usage(
    limit: int = 50,
    service: AIService = Depends(_service),
) -> AIUsageResponse:
    return await service.usage(limit=limit)