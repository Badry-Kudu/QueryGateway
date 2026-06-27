"""Schemas for the admin authentication endpoints."""

from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field

from app.auth.hashing import validate_password_length


class LoginRequest(BaseModel):
    """Body of POST /api/v1/auth/login."""

    username: str = Field(min_length=1, max_length=255)
    # Bounded to bcrypt's 72-byte limit (L4): input beyond it is ignored by
    # the hash, so a longer value can never authenticate as typed.
    password: Annotated[str, Field(min_length=1), AfterValidator(validate_password_length)]


class TokenResponse(BaseModel):
    """Response of POST /api/v1/auth/login."""

    access_token: str
    token_type: str = "bearer"
    expires_at: datetime


class MeResponse(BaseModel):
    """Response of GET /api/v1/auth/me."""

    username: str
