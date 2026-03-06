"""Pydantic schemas for application settings."""

from datetime import datetime

from pydantic import BaseModel, Field


class SettingResponse(BaseModel):
    """Public representation of a setting."""

    key: str
    value: str
    description: str | None
    is_secret: bool
    updated_at: datetime
    updated_by: str | None

    model_config = {"from_attributes": True}


class SettingUpdate(BaseModel):
    """Payload to update a single setting."""

    value: str = Field(..., min_length=1, max_length=5000)


class SettingBulkUpdate(BaseModel):
    """Payload to update multiple settings at once."""

    settings: dict[str, str] = Field(
        ..., description="Map of setting key → new value."
    )
