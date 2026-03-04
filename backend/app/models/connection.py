"""OracleConnection model — stores Oracle data-source configurations.

Credentials (encrypted_password) are stored as raw bytes.  Encryption and
decryption are handled by the service layer in Phase 2; this model is
deliberately opaque to the cipher algorithm.
"""

import uuid
from enum import StrEnum

from sqlalchemy import Boolean, Integer, LargeBinary, String, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class OracleMode(StrEnum):
    thin = "thin"
    thick = "thick"


class OracleConnection(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Oracle connection pool configuration and credential envelope."""

    __tablename__ = "connections"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, default=1521, nullable=False)
    # Exactly one of service_name or sid must be provided (enforced in service layer).
    service_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sid: Mapped[str | None] = mapped_column(String(255), nullable=True)

    username: Mapped[str] = mapped_column(String(255), nullable=False)
    # Stored as cipher-text bytes; never returned in API responses.
    encrypted_password: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    pool_min: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    pool_max: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    pool_timeout: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    query_timeout: Mapped[int] = mapped_column(Integer, default=30, nullable=False)

    mode: Mapped[OracleMode] = mapped_column(
        SAEnum(OracleMode, name="oracle_mode"),
        default=OracleMode.thin,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, server_default=text("true")
    )
