"""Snapshot repository — raw DB access for cached query results."""

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.snapshot import Snapshot


class SnapshotRepository:
    """Data-access layer for snapshot records."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_latest_by_endpoint(self, endpoint_id: uuid.UUID) -> Snapshot | None:
        """Get the most recent snapshot for an endpoint."""
        result = await self._db.execute(
            select(Snapshot)
            .where(Snapshot.endpoint_id == endpoint_id)
            .order_by(Snapshot.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, snapshot_id: uuid.UUID) -> Snapshot | None:
        result = await self._db.execute(
            select(Snapshot).where(Snapshot.id == snapshot_id)
        )
        return result.scalar_one_or_none()

    async def get_by_endpoint(
        self, endpoint_id: uuid.UUID, *, limit: int = 10
    ) -> Sequence[Snapshot]:
        result = await self._db.execute(
            select(Snapshot)
            .where(Snapshot.endpoint_id == endpoint_id)
            .order_by(Snapshot.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def create(self, obj: Snapshot) -> Snapshot:
        self._db.add(obj)
        await self._db.flush()
        await self._db.refresh(obj)
        return obj

    async def delete_old(
        self, endpoint_id: uuid.UUID, *, keep: int = 5
    ) -> int:
        """Delete old snapshots beyond the keep count. Returns deleted count."""
        # Get IDs to keep
        keep_stmt = (
            select(Snapshot.id)
            .where(Snapshot.endpoint_id == endpoint_id)
            .order_by(Snapshot.created_at.desc())
            .limit(keep)
        )
        keep_result = await self._db.execute(keep_stmt)
        keep_ids = {row[0] for row in keep_result.all()}

        if not keep_ids:
            return 0

        # Get all snapshots for endpoint
        all_stmt = select(Snapshot).where(
            Snapshot.endpoint_id == endpoint_id,
            Snapshot.id.notin_(keep_ids),
        )
        result = await self._db.execute(all_stmt)
        old_snapshots = result.scalars().all()

        for snap in old_snapshots:
            await self._db.delete(snap)

        if old_snapshots:
            await self._db.flush()

        return len(old_snapshots)
