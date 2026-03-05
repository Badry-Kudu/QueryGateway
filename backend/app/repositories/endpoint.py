"""Endpoint repository — raw DB access for ApiEndpoint records.

All queries go through SQLAlchemy 2.0 async ORM.  No business logic here.
"""

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.endpoint import ApiEndpoint


class EndpointRepository:
    """Data-access layer for API endpoint records."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_all(self, *, active_only: bool = False) -> Sequence[ApiEndpoint]:
        stmt = select(ApiEndpoint).order_by(ApiEndpoint.name)
        if active_only:
            stmt = stmt.where(ApiEndpoint.is_active.is_(True))
        result = await self._db.execute(stmt)
        return result.scalars().all()

    async def get_by_id(self, endpoint_id: uuid.UUID) -> ApiEndpoint | None:
        result = await self._db.execute(
            select(ApiEndpoint).where(ApiEndpoint.id == endpoint_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> ApiEndpoint | None:
        result = await self._db.execute(
            select(ApiEndpoint).where(ApiEndpoint.name == name)
        )
        return result.scalar_one_or_none()

    async def get_by_path(self, path: str) -> ApiEndpoint | None:
        result = await self._db.execute(
            select(ApiEndpoint).where(ApiEndpoint.path == path)
        )
        return result.scalar_one_or_none()

    async def create(self, obj: ApiEndpoint) -> ApiEndpoint:
        self._db.add(obj)
        await self._db.flush()
        await self._db.refresh(obj)
        return obj

    async def update(self, obj: ApiEndpoint, changes: dict[str, object]) -> ApiEndpoint:
        for field, value in changes.items():
            setattr(obj, field, value)
        await self._db.flush()
        await self._db.refresh(obj)
        return obj

    async def delete(self, obj: ApiEndpoint) -> None:
        await self._db.delete(obj)
        await self._db.flush()
