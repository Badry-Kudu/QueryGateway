"""Schemas for the admin authentication endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Body of POST /api/v1/auth/login."""

    username: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=1024)


class TokenResponse(BaseModel):
    """Response of POST /api/v1/auth/login."""

    access_token: str
    token_type: str = "bearer"
    expires_at: datetime


class MeResponse(BaseModel):
    """Response of GET /api/v1/auth/me."""

    username: str
