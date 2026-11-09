"""Endpoint de salud del backend."""
from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings


router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        app=settings.APP_NAME,
        version=settings.APP_VERSION,
    )