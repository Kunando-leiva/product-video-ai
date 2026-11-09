"""Endpoints de media por proyecto."""
from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ValidationError
from app.db.session import get_session
from app.models.media import MediaRead
from app.services.media_service import MediaService


router = APIRouter(prefix="/projects/{project_id}/media", tags=["media"])


def _service(session: AsyncSession = Depends(get_session)) -> MediaService:
    return MediaService(session)


@router.get("", response_model=list[MediaRead])
async def list_media(
    project_id: str,
    service: MediaService = Depends(_service),
) -> list[MediaRead]:
    return await service.list_media(project_id)


@router.post("", response_model=MediaRead, status_code=status.HTTP_201_CREATED)
async def upload_media(
    project_id: str,
    file: UploadFile = File(...),
    service: MediaService = Depends(_service),
) -> MediaRead:
    if not file.filename:
        raise ValidationError(
            message="El archivo no tiene nombre.",
            solution="Volvé a seleccionarlo desde tu equipo.",
        )
    data = await file.read()
    return await service.upload(
        project_id=project_id,
        original_name=file.filename,
        content_type=file.content_type,
        data=data,
    )


@router.post("/{media_id}/analyze", response_model=MediaRead)
async def reanalyze_media(
    project_id: str,
    media_id: str,
    service: MediaService = Depends(_service),
) -> MediaRead:
    return await service.reanalyze(project_id, media_id)


@router.delete("/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_media(
    project_id: str,
    media_id: str,
    service: MediaService = Depends(_service),
) -> None:
    await service.delete_media(project_id, media_id)