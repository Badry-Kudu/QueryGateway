"""HTTP middleware.

RequestLoggingMiddleware:
- Generates or inherits X-Request-ID per request.
- Binds request_id, endpoint, method to structlog context vars so every log
  line emitted during the request carries these fields automatically.
- Emits a structured access-log event at the end of each request with
  status, duration_ms, and the mandatory logging fields.
- Propagates X-Request-ID in the response header for client correlation.

Implementation note
-------------------
This middleware is implemented as a **pure ASGI middleware** (not a
``BaseHTTPMiddleware`` subclass) to avoid the asyncio task-switching that
``BaseHTTPMiddleware`` introduces via ``call_next``.

``BaseHTTPMiddleware`` wraps the downstream app call in a new asyncio ``Task``.
asyncpg connections (used by SQLAlchemy's async engine) are bound to the task
that created them and cannot be used from a different task — doing so raises::

    RuntimeError: Task <Task pending …> got Future <Future pending …>
    attached to a different loop

By calling ``await self.app(scope, receive, send_wrapper)`` directly in the
same coroutine, no new task is spawned and asyncpg works correctly.
"""

import time
import uuid

import structlog
from starlette.datastructures import MutableHeaders
from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

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

        # Expose request_id via request.state so route handlers can read it.
        # ``scope`` is shared across the entire request lifecycle — any Request
        # object constructed from the same scope sees the same ``scope["state"]``.
        req = Request(scope, receive)
        req.state.request_id = request_id

        status_code: int = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                # Append X-Request-ID to the outgoing response headers.
                headers = MutableHeaders(scope=message)
                headers.append("X-Request-ID", request_id)
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
