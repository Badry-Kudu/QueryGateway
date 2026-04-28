"""Verify the access log persists even when the request session rolls back.

Phase 4 moved access-log writes off the request's ``AsyncSession`` and
onto a fresh ``AsyncSessionLocal()`` so the audit row survives request-
level rollbacks. This test exercises that invariant directly.
"""

from unittest.mock import MagicMock

import pytest
from app.models.access_log import AccessLog
from app.services.access_log import log_access
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def _fake_request(method: str = "GET", request_id: str = "rid-123") -> MagicMock:
    """Build a minimal Request stand-in suitable for log_access.

    ``request_id`` is set as a real attribute on ``state`` (rather than
    leaving MagicMock to auto-mock the lookup) so ``getattr(request.state,
    "request_id", "")`` returns a string the DB can persist.
    """
    req = MagicMock()
    req.method = method
    req.headers = {}
    req.state = MagicMock()
    req.state.request_id = request_id
    req.client = MagicMock()
    req.client.host = "127.0.0.1"
    return req


async def test_log_access_persists_outside_request_session(
    db_session: AsyncSession,
) -> None:
    """The access log row must be visible to a separate session even
    after the request session is rolled back. Also verifies that
    ``set_endpoint_id`` round-trips so the audit row links back to the
    endpoint that served the request."""
    import uuid

    endpoint_id = uuid.uuid4()
    request = _fake_request()
    async with log_access(request, path="/api/v1/data/test") as ctx:
        ctx.set_status(200)
        ctx.set_principal("alice")
        ctx.set_endpoint_id(endpoint_id)

    # Roll back the (unrelated) request-scoped session — the audit row
    # was written via its own session, so it must still be there.
    await db_session.rollback()

    result = await db_session.execute(
        select(AccessLog).where(AccessLog.path == "/api/v1/data/test"),
    )
    rows = result.scalars().all()
    assert len(rows) == 1
    assert rows[0].status_code == 200
    assert rows[0].principal == "alice"
    assert rows[0].endpoint_id == endpoint_id


async def test_log_access_preserves_caller_set_status_on_unhandled_exception(
    db_session: AsyncSession,
) -> None:
    """If the body called ``set_status`` before raising, that value must
    win over the 500 fallback in the unhandled-exception branch."""
    request = _fake_request()
    with pytest.raises(RuntimeError):
        async with log_access(request, path="/api/v1/data/preset") as ctx:
            ctx.set_status(418)  # client-visible status set deliberately
            raise RuntimeError("unrelated background failure")

    rows = (
        await db_session.execute(
            select(AccessLog).where(AccessLog.path == "/api/v1/data/preset"),
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].status_code == 418


async def test_log_access_uses_header_request_id_over_state(
    db_session: AsyncSession,
) -> None:
    """An incoming ``X-Request-ID`` header must override the ID the
    middleware put on ``request.state``. Caller-supplied correlation IDs
    are how external systems trace a request across service boundaries,
    so they take precedence over the server-generated fallback."""
    request = _fake_request(request_id="rid-state")
    request.headers = {"X-Request-ID": "rid-header"}

    async with log_access(request, path="/api/v1/data/rid-precedence") as ctx:
        ctx.set_status(200)

    row = (
        await db_session.execute(
            select(AccessLog).where(AccessLog.path == "/api/v1/data/rid-precedence"),
        )
    ).scalars().one()
    assert row.request_id == "rid-header"


async def test_log_access_rejects_unsafe_header_request_id(
    db_session: AsyncSession,
) -> None:
    """A malicious ``X-Request-ID`` (newlines, spaces, oversize) must
    not be reflected into the audit log. ``resolve_request_id`` should
    reject it and fall back to the validated state value."""
    request = _fake_request(request_id="rid-state")
    request.headers = {
        "X-Request-ID": "evil\r\nX-Injected: true\r\n" + ("A" * 500),
    }

    async with log_access(request, path="/api/v1/data/rid-unsafe") as ctx:
        ctx.set_status(200)

    row = (
        await db_session.execute(
            select(AccessLog).where(AccessLog.path == "/api/v1/data/rid-unsafe"),
        )
    ).scalars().one()
    # Header rejected → fell back to the (allow-listed) state value.
    assert row.request_id == "rid-state"


async def test_log_access_persists_when_block_raises_http_exception(
    db_session: AsyncSession,
) -> None:
    """When the protected block raises HTTPException the log still goes,
    and the recorded status_code matches what the client will see."""
    request = _fake_request()
    with pytest.raises(HTTPException):
        async with log_access(request, path="/api/v1/data/exc") as ctx:
            ctx.set_principal("bob")
            raise HTTPException(status_code=404, detail="missing")

    rows = (
        await db_session.execute(
            select(AccessLog).where(AccessLog.path == "/api/v1/data/exc"),
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].status_code == 404
    assert rows[0].principal == "bob"


async def test_log_access_persists_when_block_raises_unhandled(
    db_session: AsyncSession,
) -> None:
    """Unhandled exceptions are recorded as 500 and re-raised."""
    request = _fake_request()
    with pytest.raises(RuntimeError):
        async with log_access(request, path="/api/v1/data/boom"):
            raise RuntimeError("kaboom")

    rows = (
        await db_session.execute(
            select(AccessLog).where(AccessLog.path == "/api/v1/data/boom"),
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].status_code == 500
