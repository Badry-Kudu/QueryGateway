"""Schedule repository — raw DB access for Schedule records."""

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schedule import Schedule


class ScheduleRepository:
    """Data-access layer for schedule records."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_all(self, *, active_only: bool = False) -> Sequence[Schedule]:
        stmt = select(Schedule).order_by(Schedule.created_at.desc())
        if active_only:
            stmt = stmt.where(Schedule.is_active.is_(True))
        result = await self._db.execute(stmt)
        return result.scalars().all()

    async def get_by_id(self, schedule_id: uuid.UUID) -> Schedule | None:
        result = await self._db.execute(
            select(Schedule).where(Schedule.id == schedule_id)
        )
        return result.scalar_one_or_none()

    async def get_by_endpoint_id(self, endpoint_id: uuid.UUID) -> Schedule | None:
        result = await self._db.execute(
            select(Schedule).where(Schedule.endpoint_id == endpoint_id)
        )
        return result.scalar_one_or_none()

    async def create(self, obj: Schedule) -> Schedule:
        self._db.add(obj)
        await self._db.flush()
        await self._db.refresh(obj)
        return obj

    async def update(self, obj: Schedule, changes: dict[str, object]) -> Schedule:
        for field, value in changes.items():
            setattr(obj, field, value)
        await self._db.flush()
        await self._db.refresh(obj)
        return obj

    async def delete(self, obj: Schedule) -> None:
        await self._db.delete(obj)
        await self._db.flush()
