"""Async context manager that writes one access-log row per request.

Two design points worth flagging:

1. **Dedicated session.** The previous implementation wrote to the same
   ``AsyncSession`` the request handler used. If the request rolled back
   (e.g. a SQL execution failure inside an open transaction), the access
   log row went with it — the audit trail silently disappeared exactly
   when it was most useful. Here, every write opens its own session via
   ``AsyncSessionLocal()`` so it commits independently.

2. **Errors are swallowed.** Logging failures must never bubble up and
   alter the user-visible response. We log a warning and move on.

Usage::

    async with log_access(request, path="/api/v1/data/foo") as ctx:
        ctx.set_endpoint_id(ep.id)
        ctx.set_principal("alice")
        ctx.set_status(200)
        return JSONResponse(...)

The context manager times the block automatically; the inner code only
needs to update the mutable fields it discovers.  Any exception raised
inside the block is recorded with status 500 (unless the body already
called ``set_status``) and re-raised so FastAPI can render the response.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

import structlog
from fastapi import HTTPException, Request

from app import database
from app.models.access_log import AccessLog

log = structlog.get_logger()


_DEFAULT_STATUS = 500


@dataclass
class AccessLogContext:
    """Mutable handle handed to the protected block.

    The ``log_access`` context manager fills in ``duration_ms`` on exit;
    callers are responsible for the rest.
    """

    request: Request
    path: str
    status_code: int = _DEFAULT_STATUS
    principal: str | None = None
    endpoint_id: uuid.UUID | None = None

    def set_status(self, status_code: int) -> None:
        self.status_code = status_code

    def set_principal(self, principal: str | None) -> None:
        self.principal = principal

    def set_endpoint_id(self, endpoint_id: uuid.UUID | None) -> None:
        self.endpoint_id = endpoint_id


@asynccontextmanager
async def log_access(
    request: Request,
    *,
    path: str,
) -> AsyncIterator[AccessLogContext]:
    ctx = AccessLogContext(request=request, path=path)
    start = time.monotonic()
    try:
        yield ctx
    except HTTPException as exc:
        # FastAPI translates the exception into a JSON response, so the
        # status code on the exception is the one the client will see.
        # That always wins — it represents reality.
        ctx.status_code = exc.status_code
        await _write(ctx, duration_ms=(time.monotonic() - start) * 1000)
        raise
    except Exception:
        # Unhandled error: only fall back to 500 if the body hasn't
        # already recorded a more specific status (e.g. a handler that
        # returned and then failed in a finalizer).
        if ctx.status_code == _DEFAULT_STATUS:
            ctx.status_code = 500
        await _write(ctx, duration_ms=(time.monotonic() - start) * 1000)
        raise
    else:
        await _write(ctx, duration_ms=(time.monotonic() - start) * 1000)


async def _write(ctx: AccessLogContext, *, duration_ms: float) -> None:
    """Persist one row using a fresh session so the request's transaction
    state can never poison or be poisoned by the access log."""
    # ``RequestLoggingMiddleware`` populates ``request.state.request_id``;
    # accept ``X-Request-ID`` from the client too, in that order, so
    # caller-supplied correlation IDs win when present.
    request_id = ctx.request.headers.get("X-Request-ID") or getattr(
        ctx.request.state, "request_id", ""
    )
    try:
        async with database.AsyncSessionLocal() as session:
            session.add(
                AccessLog(
                    endpoint_id=ctx.endpoint_id,
                    path=ctx.path,
                    method=ctx.request.method,
                    principal=ctx.principal,
                    remote_ip=ctx.request.client.host if ctx.request.client else None,
                    status_code=ctx.status_code,
                    duration_ms=round(duration_ms, 2),
                    request_id=request_id,
                ),
            )
            await session.commit()
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "access_log_write_failed",
            error=str(exc),
            request_id=request_id,
            user=ctx.principal or "anonymous",
            endpoint=ctx.path,
            status=ctx.status_code,
            duration_ms=round(duration_ms, 2),
            method=ctx.request.method,
            client_ip=ctx.request.client.host if ctx.request.client else None,
        )
