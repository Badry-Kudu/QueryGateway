"""Schedule repository — raw DB access for Schedule records."""

import uuid
from collections.abc import Sequence

from sqlalchemy import select

from app.models.schedule import Schedule
from app.repositories.base import BaseCrudRepository


class ScheduleRepository(BaseCrudRepository[Schedule]):
    """Data-access layer for schedule records."""

    model = Schedule

    async def get_all(self, *, active_only: bool = False) -> Sequence[Schedule]:
        stmt = select(Schedule).order_by(Schedule.created_at.desc())
        if active_only:
            stmt = stmt.where(Schedule.is_active.is_(True))
        result = await self._db.execute(stmt)
        return result.scalars().all()

    async def get_by_endpoint_id(self, endpoint_id: uuid.UUID) -> Schedule | None:
        result = await self._db.execute(
            select(Schedule).where(Schedule.endpoint_id == endpoint_id)
        )
        return result.scalar_one_or_none()
