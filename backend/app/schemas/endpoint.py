"""Pydantic schemas for API endpoint management (Phase 4).

Public contract rules:
- ``sql_text`` must use named bind parameters (``:`param_name``).
- ``path`` must be a valid URL segment (no leading slash, no whitespace).
- ``param_schema_json`` maps parameter names to type/required/default descriptors.
- ``column_map_json`` maps source column names to output names (optional).
"""

import re
import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.endpoint import DataStrategy

# Regex to find named bind parameters in Oracle SQL (:param_name).
_BIND_PARAM_RE = re.compile(r":([A-Za-z_]\w*)")

# Reject obvious string-interpolation patterns that bypass bind variables.
_UNSAFE_PATTERNS = [
    re.compile(r"'\s*\+"),  # ' +
    re.compile(r"\+\s*'"),  # + '
    re.compile(r"'\s*\|\|"),  # ' ||  (PL/SQL concat)
    re.compile(r"\|\|\s*'"),  # || '
    re.compile(r"\bf['\"]"),  # Python f-string (f' / f")
    re.compile(r"\{[^}]+\}"),  # Template interpolation {var}
    re.compile(r"\$\{"),  # ${var}
]

# Valid path segment: lowercase alphanumeric, hyphens, underscores, slashes.
_PATH_RE = re.compile(r"^[a-z0-9][a-z0-9\-_/]*$")


def extract_bind_params(sql: str) -> list[str]:
    """Return deduplicated bind parameter names from SQL text."""
    # Exclude matches inside single-quoted string literals.
    cleaned = re.sub(r"'[^']*'", "", sql)
    return list(dict.fromkeys(_BIND_PARAM_RE.findall(cleaned)))


def validate_sql_safety(sql: str) -> list[str]:
    """Return a list of safety violation messages (empty if safe)."""
    errors: list[str] = []
    for pattern in _UNSAFE_PATTERNS:
        if pattern.search(sql):
            errors.append(
                f"SQL contains potentially unsafe interpolation pattern: {pattern.pattern}"
            )
    return errors


class ParamDescriptor(BaseModel):
    """Schema for a single bind parameter."""

    type: str = Field(
        "string",
        description="Parameter type: string, integer, float, date, boolean.",
        pattern=r"^(string|integer|float|date|boolean)$",
    )
    required: bool = True
    default: str | int | float | bool | None = None
    description: str | None = None


class EndpointCreate(BaseModel):
    """Payload for POST /api/v1/admin/endpoints."""

    name: str = Field(..., min_length=1, max_length=255, description="Unique display name.")
    description: str | None = Field(None, max_length=1000)
    path: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="URL path segment after /api/v1/data/ — must be unique.",
    )
    connection_id: uuid.UUID = Field(..., description="Oracle connection to use.")
    sql_text: str = Field(..., min_length=1, description="Parameterized SQL query.")
    param_schema: dict[str, ParamDescriptor] = Field(
        default_factory=dict,
        description="Bind parameter definitions.",
    )
    column_map: dict[str, str] = Field(
        default_factory=dict,
        description="Optional output column rename map: {source_col: output_col}.",
    )
    auth_method_id: uuid.UUID | None = Field(
        None, description="Auth method to enforce on this endpoint."
    )
    data_strategy: DataStrategy = DataStrategy.live
    is_active: bool = True

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        v = v.strip("/").lower()
        if not _PATH_RE.match(v):
            raise ValueError(
                "Path must contain only lowercase alphanumeric, hyphens, underscores, or slashes."
            )
        return v

    @field_validator("sql_text")
    @classmethod
    def validate_sql(cls, v: str) -> str:
        errors = validate_sql_safety(v)
        if errors:
            raise ValueError("; ".join(errors))
        return v


class EndpointUpdate(BaseModel):
    """Payload for PUT /api/v1/admin/endpoints/{id}.

    All fields optional; omitted fields are left unchanged.
    """

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    path: str | None = Field(None, min_length=1, max_length=500)
    connection_id: uuid.UUID | None = None
    sql_text: str | None = Field(None, min_length=1)
    param_schema: dict[str, ParamDescriptor] | None = None
    column_map: dict[str, str] | None = None
    auth_method_id: uuid.UUID | None = None
    data_strategy: DataStrategy | None = None
    is_active: bool | None = None
    is_deprecated: bool | None = None
    deprecation_note: str | None = Field(None, max_length=1000)

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip("/").lower()
        if not _PATH_RE.match(v):
            raise ValueError(
                "Path must contain only lowercase alphanumeric, hyphens, underscores, or slashes."
            )
        return v

    @field_validator("sql_text")
    @classmethod
    def validate_sql(cls, v: str | None) -> str | None:
        if v is None:
            return v
        errors = validate_sql_safety(v)
        if errors:
            raise ValueError("; ".join(errors))
        return v


class EndpointResponse(BaseModel):
    """Read representation for API endpoints."""

    id: uuid.UUID
    name: str
    description: str | None
    path: str
    connection_id: uuid.UUID
    sql_text: str
    param_schema: dict[str, ParamDescriptor]
    column_map: dict[str, str]
    auth_method_id: uuid.UUID | None
    data_strategy: DataStrategy
    version: str
    is_active: bool
    is_deprecated: bool
    deprecation_note: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SqlPreviewRequest(BaseModel):
    """Request body for SQL preview execution."""

    connection_id: uuid.UUID
    sql_text: str = Field(..., min_length=1)
    params: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    max_rows: int = Field(10, ge=1, le=100)

    @field_validator("sql_text")
    @classmethod
    def validate_sql(cls, v: str) -> str:
        errors = validate_sql_safety(v)
        if errors:
            raise ValueError("; ".join(errors))
        return v


class SqlPreviewResponse(BaseModel):
    """Response from SQL preview execution."""

    columns: list[str]
    rows: list[dict[str, object]]
    row_count: int
    bind_params: list[str]
    duration_ms: float


class DataEndpointResponse(BaseModel):
    """Response from dynamic data endpoints."""

    data: list[dict[str, object]]
    meta: dict[str, object]
