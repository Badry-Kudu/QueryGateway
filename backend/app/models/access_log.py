"""AccessLog model — append-only per-request audit trail.

Intentionally uses no FK constraint on endpoint_id so log records survive
endpoint deletion.  endpoint_id is stored as a plain UUID column.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class AccessLog(UUIDPrimaryKeyMixin, Base):
    """Immutable access audit record written after each inbound request.

    Written by access-log middleware (introduced in Phase 3).  The table
    is created here in Phase 1 so the migration is consistent.
    """

    __tablename__ = "access_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    # Stored as plain UUID — no FK so records survive endpoint deletion.
    endpoint_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)

    path: Mapped[str] = mapped_column(String(500), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    # Principal identifier (username, token subject, API key label).
    principal: Mapped[str | None] = mapped_column(String(255), nullable=True)
    remote_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)

    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
