"""AuthMethod repository — raw DB access for AuthMethod records."""

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth_method import AuthMethod


class AuthMethodRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_all(self, *, active_only: bool = False) -> Sequence[AuthMethod]:
        stmt = select(AuthMethod).order_by(AuthMethod.name)
        if active_only:
            stmt = stmt.where(AuthMethod.is_active.is_(True))
        result = await self._db.execute(stmt)
        return result.scalars().all()

    async def get_by_id(self, auth_id: uuid.UUID) -> AuthMethod | None:
        result = await self._db.execute(
            select(AuthMethod).where(AuthMethod.id == auth_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> AuthMethod | None:
        result = await self._db.execute(
            select(AuthMethod).where(AuthMethod.name == name)
        )
        return result.scalar_one_or_none()

    async def create(self, obj: AuthMethod) -> AuthMethod:
        self._db.add(obj)
        await self._db.flush()
        await self._db.refresh(obj)
        return obj

    async def update(self, obj: AuthMethod, changes: dict[str, object]) -> AuthMethod:
        for field, value in changes.items():
            setattr(obj, field, value)
        await self._db.flush()
        await self._db.refresh(obj)
        return obj

    async def delete(self, obj: AuthMethod) -> None:
        await self._db.delete(obj)
        await self._db.flush()
