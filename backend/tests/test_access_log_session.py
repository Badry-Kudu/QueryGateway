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


def _fake_request(method: str = "GET") -> MagicMock:
    """Build a minimal Request stand-in suitable for log_access."""
    req = MagicMock()
    req.method = method
    req.headers = {}
    req.state.__dict__ = {}
    req.client = MagicMock()
    req.client.host = "127.0.0.1"
    return req


async def test_log_access_persists_outside_request_session(
    db_session: AsyncSession,
) -> None:
    """The access log row must be visible to a separate session even
    after the request session is rolled back."""
    request = _fake_request()
    async with log_access(request, path="/api/v1/data/test") as ctx:
        ctx.set_status(200)
        ctx.set_principal("alice")

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
