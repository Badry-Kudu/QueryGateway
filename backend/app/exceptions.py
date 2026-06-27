"""Global exception handlers registered on the FastAPI application.

All handlers return structured JSON bodies with a consistent ``detail`` key
so API consumers can parse errors uniformly.  Sensitive error detail is never
leaked in 5xx responses — only the structured log carries full context.
"""

import structlog
from fastapi import Request
from fastapi.encoders import jsonable_encoder
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
    """Handle Pydantic request-body validation errors (422).

    ``exc.errors()`` can embed a non-JSON-serializable object in each
    error's ``ctx`` (e.g. the original ``ValueError`` raised by a Pydantic
    ``model_validator``/``field_validator``). Passing that straight to
    ``JSONResponse`` raises ``TypeError`` and turns a 422 into a 500, which
    violates §3.4 (invalid input must return 422, never 500). Run the errors
    through ``jsonable_encoder`` first — matching FastAPI's own default
    handler — so those contexts are coerced to strings and the response is
    always serializable.
    """
    assert isinstance(exc, RequestValidationError)
    errors = jsonable_encoder(exc.errors())
    log.warning("request_validation_error", errors=errors)
    return JSONResponse(
        status_code=422,
        content={"detail": errors},
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
