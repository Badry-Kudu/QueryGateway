"""AppSetting model — key-value application settings store.

Settings that override Pydantic config at runtime are persisted here.
Secret settings (is_secret=True) must have their value encrypted before
write (service layer responsibility).
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class AppSetting(UUIDPrimaryKeyMixin, Base):
    """Runtime-mutable application settings with audit metadata."""

    __tablename__ = "app_settings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    # JSON-serialised string for complex values; plain string for scalars.
    value: Mapped[str] = mapped_column(String(5000), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    is_secret: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, server_default=text("false")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    # Identity of the admin who last changed this setting.
    updated_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
