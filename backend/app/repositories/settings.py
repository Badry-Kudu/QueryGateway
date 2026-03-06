"""Settings repository — raw DB access for AppSetting records."""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.setting import AppSetting


class SettingsRepository:
    """Data-access layer for application settings."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_all(self) -> Sequence[AppSetting]:
        result = await self._db.execute(
            select(AppSetting).order_by(AppSetting.key)
        )
        return result.scalars().all()

    async def get_by_key(self, key: str) -> AppSetting | None:
        result = await self._db.execute(
            select(AppSetting).where(AppSetting.key == key)
        )
        return result.scalar_one_or_none()

    async def upsert(
        self,
        key: str,
        value: str,
        *,
        description: str | None = None,
        is_secret: bool = False,
        updated_by: str | None = None,
    ) -> AppSetting:
        """Create or update a setting by key."""
        obj = await self.get_by_key(key)
        if obj is None:
            obj = AppSetting(
                key=key,
                value=value,
                description=description,
                is_secret=is_secret,
                updated_by=updated_by,
            )
            self._db.add(obj)
        else:
            obj.value = value
            if updated_by is not None:
                obj.updated_by = updated_by
        await self._db.flush()
        await self._db.refresh(obj)
        return obj

    async def delete(self, obj: AppSetting) -> None:
        await self._db.delete(obj)
        await self._db.flush()
