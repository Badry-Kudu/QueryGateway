"""Structured logging configuration via structlog.

Call configure_logging() once at application startup.  After that, obtain a
logger anywhere with:

    import structlog
    log = structlog.get_logger()

Every log event automatically carries the contextvars bound by the request
middleware (request_id, endpoint, method, user).
"""

import logging
from collections.abc import Mapping, MutableMapping
from typing import Any

import structlog

# Keys whose values must never reach the log sink, even if a caller binds one
# by mistake (L2 — defence in depth, §3.5). Matched case-insensitively against
# the exact key name. The mandatory field set (request_id, user, endpoint,
# status, duration_ms, event) and scheduler fields are deliberately excluded.
_SENSITIVE_KEYS = frozenset(
    {
        "password",
        "secret",
        "token",
        "api_key",
        "key",
        "authorization",
        "signing_secret",
    }
)
_REDACTED = "***REDACTED***"


def _redact_value(value: Any) -> Any:
    """Recursively redact sensitive keys inside nested mappings/sequences."""
    if isinstance(value, Mapping):
        return {
            k: (
                _REDACTED
                if isinstance(k, str) and k.lower() in _SENSITIVE_KEYS
                else _redact_value(v)
            )
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_redact_value(v) for v in value]
    if isinstance(value, tuple):
        return tuple(_redact_value(v) for v in value)
    return value


def redact_sensitive(
    _logger: Any, _method_name: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """structlog processor that masks values for known-sensitive keys.

    Runs immediately before the renderer so it covers every event regardless
    of where it was bound (contextvars, call-site kwargs, etc.). Recurses into
    nested mappings/lists/tuples so secrets buried inside structured values
    (e.g. ``headers.authorization``, ``payload.api_key``) are masked too.
    """
    for k, v in list(event_dict.items()):
        if isinstance(k, str) and k.lower() in _SENSITIVE_KEYS:
            event_dict[k] = _REDACTED
        else:
            event_dict[k] = _redact_value(v)
    return event_dict


def configure_logging(log_level: str = "INFO") -> None:
    """Wire structlog for structured JSON output.

    Processors (in order):
    1. Merge any context vars set by middleware (request_id, user, etc.)
    2. Add stdlib log level name.
    3. Add ISO-8601 timestamp.
    4. Render exception info (if any).
    5. Redact known-sensitive keys (defence in depth).
    6. Render to JSON.
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    logging.basicConfig(
        format="%(message)s",
        level=level,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.ExceptionRenderer(),
            redact_sensitive,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
