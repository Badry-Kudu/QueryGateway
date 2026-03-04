"""Pydantic schemas for auth method management.

Public contract rules:
- Secrets (signing_secret, password, api_key) are NEVER returned in responses.
- After creation of bearer/api_key methods a one-time credential is returned
  in a separate `TokenIssuedResponse` / `ApiKeyIssuedResponse` schema.
- `config_json` is opaque to the API layer — only metadata is surfaced.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.models.auth_method import AuthMethodType

# ── Create ────────────────────────────────────────────────────────────────────


class AuthMethodCreate(BaseModel):
    """Payload for POST /api/v1/admin/auth/.

    Type-specific fields are validated by model_validator.
    """

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    method_type: AuthMethodType
    is_active: bool = True

    # Bearer-specific
    algorithm: str = Field("HS256", description="JWT signing algorithm.")
    expire_minutes: int = Field(60, ge=1, le=525_600)  # max 1 year

    # Basic-specific
    username: str | None = Field(None, min_length=1, max_length=255)
    password: str | None = Field(
        None, min_length=1, description="Plaintext — hashed before storage."
    )

    # API-key-specific
    key_prefix: str = Field("db2api_", max_length=32)

    @model_validator(mode="after")
    def validate_type_fields(self) -> "AuthMethodCreate":
        if self.method_type == AuthMethodType.basic:
            if not self.username:
                raise ValueError("username is required for basic auth.")
            if not self.password:
                raise ValueError("password is required for basic auth.")
        return self


# ── Update ────────────────────────────────────────────────────────────────────


class AuthMethodUpdate(BaseModel):
    """Payload for PUT /api/v1/admin/auth/{id}. All fields optional."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    is_active: bool | None = None

    # Bearer
    expire_minutes: int | None = Field(None, ge=1, le=525_600)

    # Basic — rotate password
    username: str | None = Field(None, min_length=1, max_length=255)
    password: str | None = Field(None, min_length=1)


# ── Read ──────────────────────────────────────────────────────────────────────


class AuthMethodResponse(BaseModel):
    """Read representation — no secrets, no hashes."""

    id: uuid.UUID
    name: str
    description: str | None
    method_type: AuthMethodType
    is_active: bool
    # Derived metadata surfaced per type (no secret values).
    algorithm: str | None          # bearer only
    expire_minutes: int | None     # bearer only
    username: str | None           # basic only
    key_prefix: str | None         # api_key only
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── One-time credential responses ─────────────────────────────────────────────


class TokenIssuedResponse(BaseModel):
    """Returned by POST /api/v1/admin/auth/{id}/issue-token (bearer only)."""

    token: str
    token_type: str = "bearer"
    expires_at: datetime
    note: str = "Store this token securely. It is not saved server-side."


class ApiKeyIssuedResponse(BaseModel):
    """Returned once after creation or rotation of an api_key auth method."""

    api_key: str
    note: str = "This key is shown once only. Store it securely."


class RotateResponse(BaseModel):
    """Generic rotate confirmation for bearer (new secret generated)."""

    message: str
