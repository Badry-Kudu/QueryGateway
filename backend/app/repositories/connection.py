"""Connection repository — raw DB access for OracleConnection records.

All queries go through SQLAlchemy 2.0 async ORM.  No business logic here.
"""

from collections.abc import Sequence

from sqlalchemy import select

from app.models.connection import OracleConnection
from app.repositories.base import BaseCrudRepository


class ConnectionRepository(BaseCrudRepository[OracleConnection]):
    """Data-access layer for Oracle connection records."""

    model = OracleConnection

    async def get_all(self, *, active_only: bool = False) -> Sequence[OracleConnection]:
        stmt = select(OracleConnection).order_by(OracleConnection.name)
        if active_only:
            stmt = stmt.where(OracleConnection.is_active.is_(True))
        result = await self._db.execute(stmt)
        return result.scalars().all()

    async def get_by_name(self, name: str) -> OracleConnection | None:
        result = await self._db.execute(
            select(OracleConnection).where(OracleConnection.name == name)
        )
        return result.scalar_one_or_none()
