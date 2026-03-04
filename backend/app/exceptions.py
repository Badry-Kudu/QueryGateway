"""Global exception handlers registered on the FastAPI application.

All handlers return structured JSON bodies with a consistent ``detail`` key
so API consumers can parse errors uniformly.  Sensitive error detail is never
leaked in 5xx responses — only the structured log carries full context.
"""

import structlog
from fastapi import Request
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse

log = structlog.get_logger()


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle FastAPI/Starlette HTTPException."""
    assert isinstance(exc, HTTPException)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=dict(exc.headers) if exc.headers else {},
    )


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle Pydantic request-body validation errors (422)."""
    assert isinstance(exc, RequestValidationError)
    log.warning("request_validation_error", errors=exc.errors())
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unexpected server errors.

    Logs the full traceback via structlog (which carries request_id from
    context vars) but returns only a generic 500 body to the client.
    """
    log.exception("unhandled_exception", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
