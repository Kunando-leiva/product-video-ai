"""Acceso a datos de TimelineItem."""
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import TimelineItem


class TimelineRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_by_project(self, project_id: str) -> Sequence[TimelineItem]:
        result = await self.session.execute(
            select(TimelineItem)
            .where(TimelineItem.project_id == project_id)
            .order_by(TimelineItem.order_index.asc())
        )
        return result.scalars().all()

    async def get(self, item_id: str) -> Optional[TimelineItem]:
        return await self.session.get(TimelineItem, item_id)

    async def delete_by_project(self, project_id: str) -> None:
        items = await self.list_by_project(project_id)
        for it in items:
            await self.session.delete(it)

    async def add(self, item: TimelineItem) -> TimelineItem:
        self.session.add(item)
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def commit(self) -> None:
        await self.session.commit()

    async def refresh(self, item: TimelineItem) -> None:
        await self.session.refresh(item)

    async def replace_all(
        self, project_id: str, new_items: list[TimelineItem]
    ) -> list[TimelineItem]:
        """Reemplazo atómico: borra todos los items del proyecto e inserta los nuevos."""
        await self.delete_by_project(project_id)
        for it in new_items:
            self.session.add(it)
        await self.session.commit()
        for it in new_items:
            await self.session.refresh(it)
        return new_items