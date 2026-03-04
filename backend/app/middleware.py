"""HTTP middleware.

RequestLoggingMiddleware:
- Generates or inherits X-Request-ID per request.
- Binds request_id, endpoint, method to structlog context vars so every log
  line emitted during the request carries these fields automatically.
- Emits a structured access-log event at the end of each request with
  status, duration_ms, and the mandatory logging fields.
- Propagates X-Request-ID in the response header for client correlation.
"""

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

log = structlog.get_logger()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: object) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        # Establish per-request log context visible to all downstream loggers.
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            endpoint=request.url.path,
            method=request.method,
            user="anonymous",  # Updated by auth middleware in later phases.
        )

        start = time.perf_counter()
        try:
            # call_next is a callable provided by Starlette's BaseHTTPMiddleware.
            response: Response = await call_next(request)  # type: ignore[operator]
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            log.info(
                "request_completed",
                status=response.status_code,
                duration_ms=duration_ms,
            )
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            log.exception("request_failed", duration_ms=duration_ms)
            raise
