"""AuthMethod repository — raw DB access for AuthMethod records."""

from collections.abc import Sequence

from sqlalchemy import select

from app.models.auth_method import AuthMethod
from app.repositories.base import BaseCrudRepository


class AuthMethodRepository(BaseCrudRepository[AuthMethod]):
    """Data-access layer for auth method records."""

    model = AuthMethod

    async def get_all(self, *, active_only: bool = False) -> Sequence[AuthMethod]:
        stmt = select(AuthMethod).order_by(AuthMethod.name)
        if active_only:
            stmt = stmt.where(AuthMethod.is_active.is_(True))
        result = await self._db.execute(stmt)
        return result.scalars().all()

    async def get_by_name(self, name: str) -> AuthMethod | None:
        result = await self._db.execute(
            select(AuthMethod).where(AuthMethod.name == name)
        )
        return result.scalar_one_or_none()
