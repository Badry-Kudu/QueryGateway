"""HTTP middleware.

RequestLoggingMiddleware:
- Generates or inherits X-Request-ID per request.
- Binds request_id, endpoint, method to structlog context vars so every log
  line emitted during the request carries these fields automatically.
- Emits a structured access-log event at the end of each request with
  status, duration_ms, and the mandatory logging fields.
- Propagates X-Request-ID in the response header for client correlation.

Implemented as a pure ASGI middleware (not BaseHTTPMiddleware) so that
``await self.app(scope, receive, send_wrapper)`` runs in the *same*
coroutine/task as the caller.  BaseHTTPMiddleware wraps call_next in a
new asyncio Task, which breaks asyncpg connections that are task-bound.
"""

import time
import uuid
from typing import Any

import structlog
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

log = structlog.get_logger()


class RequestLoggingMiddleware:
    """Pure ASGI request-logging middleware with X-Request-ID propagation."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Extract or generate the correlation ID from the incoming request.
        request_id: str | None = None
        for header_name, header_value in scope.get("headers", []):
            if header_name.lower() == b"x-request-id":
                request_id = header_value.decode(errors="replace")
                break
        if not request_id:
            request_id = str(uuid.uuid4())

        path: str = scope.get("path", "")
        method: str = scope.get("method", "")

        # Establish per-request log context visible to all downstream loggers.
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            endpoint=path,
            method=method,
            user="anonymous",  # Updated by auth middleware in later phases.
        )

        status_code: int = 0

        async def send_wrapper(message: Any) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                # Inject X-Request-ID into the response headers.
                headers = list(message.get("headers", []))
                headers.append(
                    (b"x-request-id", request_id.encode())
                )
                message = {**message, "headers": headers}
            await send(message)

        start = time.perf_counter()
        try:
            await self.app(scope, receive, send_wrapper)
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            log.info(
                "request_completed",
                status=status_code,
                duration_ms=duration_ms,
            )
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            log.exception("request_failed", duration_ms=duration_ms)
            raise
