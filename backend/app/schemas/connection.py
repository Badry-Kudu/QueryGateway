"""Pydantic schemas for Oracle connection management.

Public contract rules:
- `password` is accepted on write operations only.
- `encrypted_password` is NEVER exposed outside the service layer.
- Responses include `has_password: bool` to indicate credentials are stored.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.models.connection import OracleMode


class ConnectionBase(BaseModel):
    """Fields shared by create and update payloads."""

    name: str = Field(..., min_length=1, max_length=255, description="Unique display name.")
    description: str | None = Field(None, max_length=1000)

    host: str = Field(..., min_length=1, max_length=255, description="Oracle host or IP.")
    port: int = Field(1521, ge=1, le=65535)
    service_name: str | None = Field(None, max_length=255)
    sid: str | None = Field(None, max_length=255)

    username: str = Field(..., min_length=1, max_length=255)

    pool_min: int = Field(1, ge=0, le=100)
    pool_max: int = Field(5, ge=1, le=100)
    pool_timeout: int = Field(30, ge=1, le=3600, description="Seconds to wait for a pool slot.")
    query_timeout: int = Field(
        30, ge=1, le=3600, description="Seconds before a query is cancelled."
    )

    mode: OracleMode = OracleMode.thin
    is_active: bool = True

    @model_validator(mode="after")
    def require_service_name_or_sid(self) -> "ConnectionBase":
        if not self.service_name and not self.sid:
            raise ValueError("Exactly one of service_name or sid must be provided.")
        if self.service_name and self.sid:
            raise ValueError("Provide either service_name or sid, not both.")
        return self

    @model_validator(mode="after")
    def pool_min_le_max(self) -> "ConnectionBase":
        if self.pool_min > self.pool_max:
            raise ValueError("pool_min must be ≤ pool_max.")
        return self


class ConnectionCreate(ConnectionBase):
    """Payload for POST /api/v1/admin/connections."""

    password: str = Field(..., min_length=1, description="Plaintext — encrypted before storage.")


class ConnectionUpdate(BaseModel):
    """Payload for PUT /api/v1/admin/connections/{id}.

    All fields are optional; omitted fields are left unchanged.
    Supplying `password=null` is ignored — use an explicit string to rotate.
    """

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None

    host: str | None = Field(None, min_length=1, max_length=255)
    port: int | None = Field(None, ge=1, le=65535)
    service_name: str | None = Field(None, max_length=255)
    sid: str | None = Field(None, max_length=255)

    username: str | None = Field(None, min_length=1, max_length=255)
    password: str | None = Field(
        None, min_length=1, description="Rotate password; omit to keep current."
    )

    pool_min: int | None = Field(None, ge=0, le=100)
    pool_max: int | None = Field(None, ge=1, le=100)
    pool_timeout: int | None = Field(None, ge=1, le=3600)
    query_timeout: int | None = Field(None, ge=1, le=3600)

    mode: OracleMode | None = None
    is_active: bool | None = None


class ConnectionResponse(BaseModel):
    """Read representation — never contains password or encrypted_password."""

    id: uuid.UUID
    name: str
    description: str | None
    host: str
    port: int
    service_name: str | None
    sid: str | None
    username: str
    has_password: bool
    pool_min: int
    pool_max: int
    pool_timeout: int
    query_timeout: int
    mode: OracleMode
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConnectionTestResult(BaseModel):
    """Result of POST /api/v1/admin/connections/{id}/test."""

    success: bool
    message: str
    duration_ms: float | None = None
    oracle_version: str | None = None
