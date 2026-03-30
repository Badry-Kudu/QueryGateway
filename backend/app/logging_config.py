"""Structured logging configuration via structlog.

Call configure_logging() once at application startup.  After that, obtain a
logger anywhere with:

    import structlog
    log = structlog.get_logger()

Every log event automatically carries the contextvars bound by the request
middleware (request_id, endpoint, method, user).
"""

import logging

import structlog


def configure_logging(log_level: str = "INFO") -> None:
    """Wire structlog for structured JSON output.

    Processors (in order):
    1. Merge any context vars set by middleware (request_id, user, etc.)
    2. Add stdlib log level name.
    3. Add ISO-8601 timestamp.
    4. Render exception info (if any).
    5. Render to JSON.
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
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
