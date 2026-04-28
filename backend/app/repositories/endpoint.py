"""Endpoint repository — raw DB access for ApiEndpoint records.

All queries go through SQLAlchemy 2.0 async ORM.  No business logic here.
"""

from collections.abc import Sequence

from sqlalchemy import select

from app.models.endpoint import ApiEndpoint
from app.repositories.base import BaseCrudRepository


class EndpointRepository(BaseCrudRepository[ApiEndpoint]):
    """Data-access layer for API endpoint records."""

    model = ApiEndpoint

    async def get_all(self, *, active_only: bool = False) -> Sequence[ApiEndpoint]:
        stmt = select(ApiEndpoint).order_by(ApiEndpoint.name)
        if active_only:
            stmt = stmt.where(ApiEndpoint.is_active.is_(True))
        result = await self._db.execute(stmt)
        return result.scalars().all()

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
