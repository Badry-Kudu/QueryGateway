"""Build a Pydantic model from a stored ``param_schema_json`` descriptor.

This replaces the hand-rolled ``_coerce_param`` loop that lived in
``app.routers.data``. Using ``pydantic.create_model`` gives us:

- Declarative validation (Pydantic surfaces the field name and reason).
- Free coercion for ints / floats / dates from request strings.
- Consistent error shape with the rest of the API.

The descriptor format mirrors ``app.schemas.endpoint.ParamDescriptor`` —
``{"type": "string|integer|float|boolean|date", "required": bool,
"default": <value>, "max_length": int | None}``.
"""

from datetime import date
from typing import Annotated, Any, Literal, get_args

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, create_model

ParamType = Literal["string", "integer", "float", "boolean", "date"]
_VALID_PARAM_TYPES = set(get_args(ParamType))

# Match the exact set the legacy ``_coerce_param`` accepted — Pydantic's
# default bool coercion is permissive about other forms (``y``, ``on``,
# truthy ints, etc.) which would silently broaden the contract.
_BOOL_TRUE = {"true", "1", "yes"}
_BOOL_FALSE = {"false", "0", "no"}


def _coerce_bool(value: object) -> object:
    """Pre-validator: accept exactly the same strings the legacy loop did.

    Pass through booleans (so a default of ``True`` round-trips) and let
    everything else fall through to Pydantic, which will raise a clear
    type error.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.lower()
        if normalized in _BOOL_TRUE:
            return True
        if normalized in _BOOL_FALSE:
            return False
        raise ValueError(
            f"expected true/false/1/0/yes/no, got '{value}'"
        )
    return value


def _build_field(descriptor: dict[str, Any]) -> tuple[type, Any]:
    """Map one descriptor to a ``(annotation, default)`` pair for ``create_model``."""
    raw_type = descriptor.get("type", "string")
    if raw_type not in _VALID_PARAM_TYPES:
        # Unknown type — treat as string. Matches the legacy fallback at
        # the bottom of ``_coerce_param``.
        raw_type = "string"

    required = bool(descriptor.get("required", True))
    default = descriptor.get("default")
    max_length = descriptor.get("max_length")

    annotation: type
    if raw_type == "integer":
        annotation = int
    elif raw_type == "float":
        annotation = float
    elif raw_type == "boolean":
        annotation = Annotated[bool, BeforeValidator(_coerce_bool)]  # type: ignore[assignment]
    elif raw_type == "date":
        annotation = date
    else:  # "string"
        annotation = str
        if isinstance(max_length, int) and max_length >= 1:
            annotation = Annotated[str, Field(max_length=max_length)]  # type: ignore[assignment]

    field_default = ... if required else default
    return annotation, field_default


def build_param_model(param_schema: dict[str, Any]) -> type[BaseModel]:
    """Construct a Pydantic model that validates ``param_schema`` payloads.

    Non-dict values in ``param_schema`` are ignored to match the legacy
    ``_coerce_param`` loop, which skipped them defensively.
    """
    fields: dict[str, tuple[type, Any]] = {}
    for name, descriptor in param_schema.items():
        if not isinstance(descriptor, dict):
            continue
        fields[name] = _build_field(descriptor)

    model = create_model(
        "EndpointParams",
        __config__=ConfigDict(extra="forbid"),
        **fields,  # type: ignore[call-overload]
    )
    return model
