"""Connection repository — raw DB access for OracleConnection records.

All queries go through SQLAlchemy 2.0 async ORM.  No business logic here.
"""

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connection import OracleConnection


class ConnectionRepository:
    """Data-access layer for Oracle connection records."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_all(self, *, active_only: bool = False) -> Sequence[OracleConnection]:
        stmt = select(OracleConnection).order_by(OracleConnection.name)
        if active_only:
            stmt = stmt.where(OracleConnection.is_active.is_(True))
        result = await self._db.execute(stmt)
        return result.scalars().all()

    async def get_by_id(self, connection_id: uuid.UUID) -> OracleConnection | None:
        result = await self._db.execute(
            select(OracleConnection).where(OracleConnection.id == connection_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> OracleConnection | None:
        result = await self._db.execute(
            select(OracleConnection).where(OracleConnection.name == name)
        )
        return result.scalar_one_or_none()

    async def create(self, obj: OracleConnection) -> OracleConnection:
        self._db.add(obj)
        await self._db.flush()
        await self._db.refresh(obj)
        return obj

    async def update(self, obj: OracleConnection, changes: dict[str, object]) -> OracleConnection:
        for field, value in changes.items():
            setattr(obj, field, value)
        await self._db.flush()
        await self._db.refresh(obj)
        return obj

    async def delete(self, obj: OracleConnection) -> None:
        await self._db.delete(obj)
        await self._db.flush()
