"""Acceso a datos de Media."""
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import Media


class MediaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_by_project(self, project_id: str) -> Sequence[Media]:
        result = await self.session.execute(
            select(Media)
            .where(Media.project_id == project_id)
            .order_by(Media.created_at.asc())
        )
        return result.scalars().all()

    async def get(self, media_id: str) -> Optional[Media]:
        return await self.session.get(Media, media_id)

    async def create(self, media: Media) -> Media:
        self.session.add(media)
        await self.session.commit()
        await self.session.refresh(media)
        return media

    async def delete(self, media: Media) -> None:
        await self.session.delete(media)
        await self.session.commit()