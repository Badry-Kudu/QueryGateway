"""Pydantic response schemas for health endpoints."""

from pydantic import BaseModel


class HealthCheck(BaseModel):
    """Standard health response body."""

    status: str
    checks: dict[str, str] = {}
