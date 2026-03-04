"""AuthMethod model — per-endpoint authentication configuration.

config_json stores method-specific settings (e.g., token expiry seconds for
Bearer, allowed keys list for API key).  Fields containing secrets inside
config_json must be encrypted before write (service layer responsibility,
Phase 3).
"""

import uuid
from enum import StrEnum

from sqlalchemy import Boolean, String, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AuthMethodType(StrEnum):
    bearer = "bearer"
    basic = "basic"
    api_key = "api_key"


class AuthMethod(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Reusable authentication method that can be assigned to any endpoint."""

    __tablename__ = "auth_methods"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    method_type: Mapped[AuthMethodType] = mapped_column(
        SAEnum(AuthMethodType, name="auth_method_type"),
        nullable=False,
    )
    # Method-specific config; shape validated by service layer per method_type.
    config_json: Mapped[dict[str, object]] = mapped_column(
        JSONB, nullable=False, default=dict
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, server_default=text("true")
    )
