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

import re
import time
import uuid
from typing import Any

import structlog
from starlette.types import ASGIApp, Receive, Scope, Send

log = structlog.get_logger()

# Allow-list for caller-supplied X-Request-ID values.  Permits the chars
# used by UUIDs (``-``), ULIDs (alnum), W3C trace IDs (hex), and
# namespaced IDs like ``svc:abc.123`` while excluding control characters,
# whitespace, ANSI escape sequences, and anything else that could poison
# a log line or be reflected back in the X-Request-ID response header.
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def _is_safe_request_id(value: object) -> bool:
    return isinstance(value, str) and bool(_REQUEST_ID_RE.match(value))


def resolve_request_id(request: Any) -> str:
    """Return a non-empty, sanitized correlation ID for ``request``.

    Resolution order (caller-supplied wins so external systems can trace
    requests across service boundaries):

    1. ``X-Request-ID`` header on the inbound request — but only if it
       passes the allow-list validation. Untrusted input is otherwise
       reflected into log lines, the persisted ``access_logs.request_id``
       column, and the response header.
    2. ``request.state.request_id`` populated by
       ``RequestLoggingMiddleware`` (also validated, in case it was set
       from elsewhere).
    3. A freshly minted UUID — guarantees logs and audit rows always
       carry a usable ID even if the middleware was bypassed (test
       harnesses that mount the app directly, or future deployments
       that strip middleware).

    ``getattr`` rather than ``request.state.__dict__.get`` because
    Starlette ``State`` routes attribute access through
    ``__setattr__``/``__getattr__``, so attributes never appear in
    ``__dict__``.
    """
    header = request.headers.get("X-Request-ID")
    if _is_safe_request_id(header):
        return header  # type: ignore[no-any-return]

    state_id = getattr(request.state, "request_id", "")
    if _is_safe_request_id(state_id):
        return state_id

    return str(uuid.uuid4())


class RequestLoggingMiddleware:
    """Pure ASGI request-logging middleware with X-Request-ID propagation."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Extract or generate the correlation ID from the incoming
        # request. Caller-supplied values are validated against the
        # allow-list *before* being bound to log context, persisted via
        # ``scope.state.request_id``, or echoed back in the response
        # header — otherwise a malicious value (CRLF, ANSI escapes,
        # 100KB blob) reaches all three sinks. ``resolve_request_id``
        # only protects route handlers that read from ``request.state``
        # *after* this middleware ran, so the validation has to happen
        # here too.
        request_id: str | None = None
        for header_name, header_value in scope.get("headers", []):
            if header_name.lower() == b"x-request-id":
                candidate = header_value.decode(errors="replace")
                if _is_safe_request_id(candidate):
                    request_id = candidate
                break
        if not request_id:
            request_id = str(uuid.uuid4())

        path: str = scope.get("path", "")
        method: str = scope.get("method", "")
        client = scope.get("client")
        client_ip: str | None = (
            str(client[0]) if isinstance(client, tuple) and len(client) > 0 else None
        )

        # Establish per-request log context visible to all downstream loggers.
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            endpoint=path,
            method=method,
            client_ip=client_ip,
            user="anonymous",  # Updated by auth middleware in later phases.
        )

        # Make the request_id reachable from FastAPI handlers via
        # ``request.state.request_id``. structlog's contextvars work for
        # log emission but route handlers that need to *propagate* the
        # ID (e.g. the access-log writer's persisted ``request_id``
        # column, or the data router's failure log) need a synchronous
        # accessor on the Request object. Starlette materializes
        # ``Request.state`` from ``scope["state"]``.
        scope_state = scope.setdefault("state", {})
        scope_state["request_id"] = request_id

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
            # ``status_code`` may still be 0 if the failure happened
            # before the response started; default to 500 so the
            # mandatory structured-log field set is always populated.
            log.exception(
                "request_failed",
                status=status_code or 500,
                duration_ms=duration_ms,
            )
            raise
