"""Acceso a datos de RenderJob."""
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import RenderJob


class RenderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_by_project(self, project_id: str) -> Sequence[RenderJob]:
        result = await self.session.execute(
            select(RenderJob)
            .where(RenderJob.project_id == project_id)
            .order_by(RenderJob.created_at.desc())
        )
        return result.scalars().all()

    async def get(self, job_id: str) -> Optional[RenderJob]:
        return await self.session.get(RenderJob, job_id)

    async def add(self, job: RenderJob) -> RenderJob:
        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def commit(self) -> None:
        await self.session.commit()

    async def refresh(self, job: RenderJob) -> None:
        await self.session.refresh(job)

    async def delete(self, job: RenderJob) -> None:
        await self.session.delete(job)
        await self.session.commit()