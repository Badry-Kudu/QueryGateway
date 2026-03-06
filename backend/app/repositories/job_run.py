"""JobRun repository — raw DB access for job execution records."""

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job_run import JobRun


class JobRunRepository:
    """Data-access layer for job run audit records."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_all(
        self,
        *,
        schedule_id: uuid.UUID | None = None,
        endpoint_id: uuid.UUID | None = None,
        limit: int = 50,
    ) -> Sequence[JobRun]:
        stmt = select(JobRun).order_by(JobRun.started_at.desc()).limit(limit)
        if schedule_id is not None:
            stmt = stmt.where(JobRun.schedule_id == schedule_id)
        if endpoint_id is not None:
            stmt = stmt.where(JobRun.endpoint_id == endpoint_id)
        result = await self._db.execute(stmt)
        return result.scalars().all()

    async def get_by_id(self, job_run_id: uuid.UUID) -> JobRun | None:
        result = await self._db.execute(
            select(JobRun).where(JobRun.id == job_run_id)
        )
        return result.scalar_one_or_none()

    async def create(self, obj: JobRun) -> JobRun:
        self._db.add(obj)
        await self._db.flush()
        await self._db.refresh(obj)
        return obj

    async def update(self, obj: JobRun, changes: dict[str, object]) -> JobRun:
        for field, value in changes.items():
            setattr(obj, field, value)
        await self._db.flush()
        await self._db.refresh(obj)
        return obj
