"""Unit tests for ``resolve_request_id`` and the middleware-level
``X-Request-ID`` validation.

Phase 4 follow-up: caller-supplied ``X-Request-ID`` headers are now
allow-listed at *both* layers — the middleware (``__call__``, primary
path) and the ``resolve_request_id`` helper (fallback for handlers
that read ``request.state``). These tests pin both contracts.
"""

import re
from unittest.mock import MagicMock

from app.middleware import resolve_request_id
from httpx import AsyncClient

_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def _request(header: object = None, state_value: object = None) -> MagicMock:
    req = MagicMock()
    req.headers = {} if header is None else {"X-Request-ID": header}
    req.state = MagicMock()
    if state_value is None:
        # Make sure ``getattr`` falls through to the default.
        del req.state.request_id
    else:
        req.state.request_id = state_value
    return req


def test_resolve_request_id_uses_safe_header() -> None:
    assert resolve_request_id(_request(header="rid-abc-123")) == "rid-abc-123"


def test_resolve_request_id_uses_state_when_header_missing() -> None:
    assert resolve_request_id(_request(state_value="state-rid-1")) == "state-rid-1"


def test_resolve_request_id_falls_back_to_uuid_when_no_input() -> None:
    out = resolve_request_id(_request())
    assert _UUID_RE.match(out)


def test_resolve_request_id_rejects_header_with_newlines() -> None:
    """CRLF in a header value would inject an extra header line if
    reflected back in a response — never trust it."""
    out = resolve_request_id(
        _request(header="rid\r\nX-Injected: pwned", state_value="state-rid-2")
    )
    assert out == "state-rid-2"


def test_resolve_request_id_rejects_header_with_spaces() -> None:
    out = resolve_request_id(_request(header="not a valid id"))
    assert _UUID_RE.match(out)


def test_resolve_request_id_rejects_oversized_header() -> None:
    """Anything beyond the 128-char allowance is dropped to keep log
    lines and the audit DB column bounded."""
    out = resolve_request_id(_request(header="A" * 200))
    assert _UUID_RE.match(out)


def test_resolve_request_id_rejects_non_string_header() -> None:
    """A bytes-like or numeric header value (some odd ASGI servers)
    must not crash the helper."""
    out = resolve_request_id(_request(header=b"binary-bytes"))
    assert _UUID_RE.match(out)


def test_resolve_request_id_rejects_unsafe_state_too() -> None:
    """The middleware should always set a safe ID, but the helper still
    validates state as a defense in depth."""
    out = resolve_request_id(_request(state_value="bad value with spaces"))
    assert _UUID_RE.match(out)


# ── Middleware-level validation ──────────────────────────────────────────────
#
# These tests drive the real ASGI app via ``http_client``. The header
# value visible on the *response* proves what the middleware bound to
# log context, persisted to ``access_logs.request_id``, and echoed
# back — all three sinks are fed from the same variable.


async def test_middleware_echoes_safe_header(http_client: AsyncClient) -> None:
    response = await http_client.get(
        "/api/v1/admin/health/live", headers={"X-Request-ID": "safe-rid-123"}
    )
    assert response.headers["x-request-id"] == "safe-rid-123"


async def test_middleware_replaces_crlf_header_with_uuid(
    http_client: AsyncClient,
) -> None:
    """If a caller sends CRLF in X-Request-ID, the middleware must NOT
    reflect it — that would inject a header line into the response and
    poison the JSON access-log entry."""
    response = await http_client.get(
        "/api/v1/admin/health/live",
        headers={"X-Request-ID": "rid\r\nX-Injected: pwned"},
    )
    echoed = response.headers["x-request-id"]
    assert _UUID_RE.match(echoed), f"expected UUID fallback, got {echoed!r}"


async def test_middleware_replaces_oversized_header_with_uuid(
    http_client: AsyncClient,
) -> None:
    response = await http_client.get(
        "/api/v1/admin/health/live", headers={"X-Request-ID": "A" * 200}
    )
    echoed = response.headers["x-request-id"]
    assert _UUID_RE.match(echoed)


async def test_middleware_replaces_header_with_spaces(
    http_client: AsyncClient,
) -> None:
    response = await http_client.get(
        "/api/v1/admin/health/live",
        headers={"X-Request-ID": "not a valid id"},
    )
    echoed = response.headers["x-request-id"]
    assert _UUID_RE.match(echoed)
