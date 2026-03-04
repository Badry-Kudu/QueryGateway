"""Health endpoint tests.

Liveness tests use the ``http_client`` fixture (no DB dependency) so they
run without a PostgreSQL instance.  Readiness tests use ``async_client``
(DB-backed) and require DATABASE_URL to be reachable — satisfied by the
Postgres service in CI.
"""

import pytest
from httpx import AsyncClient

# ── Liveness — no DB required ─────────────────────────────────────────────────


async def test_liveness_returns_ok(http_client: AsyncClient) -> None:
    response = await http_client.get("/api/v1/admin/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_liveness_propagates_request_id(http_client: AsyncClient) -> None:
    rid = "test-correlation-abc"
    response = await http_client.get(
        "/api/v1/admin/health/live", headers={"X-Request-ID": rid}
    )
    assert response.status_code == 200
    assert response.headers.get("x-request-id") == rid


async def test_liveness_generates_request_id_if_absent(http_client: AsyncClient) -> None:
    response = await http_client.get("/api/v1/admin/health/live")
    assert "x-request-id" in response.headers
    assert len(response.headers["x-request-id"]) > 0


# ── Readiness — requires live PostgreSQL (CI only) ────────────────────────────


@pytest.mark.integration
async def test_readiness_returns_ok_with_db(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/admin/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["checks"]["db"] == "ok"


@pytest.mark.integration
async def test_readiness_returns_request_id_header(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/admin/health/ready")
    assert "x-request-id" in response.headers
