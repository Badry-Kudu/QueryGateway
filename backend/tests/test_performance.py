"""Phase 7 — Performance sanity tests.

These tests validate that critical API paths respond within acceptable
latency budgets.  They do NOT measure throughput — they ensure no
regressions in response time for common admin and data operations.

Timeouts are generous (seconds, not milliseconds) since these run in
CI without tuned infrastructure.
"""

import time
import uuid

import pytest
from httpx import AsyncClient


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


@pytest.mark.integration
class TestAdminApiLatency:
    """Admin API response time sanity checks."""

    async def test_connection_list_latency(self, async_client: object) -> None:
        """GET /connections/ should respond within 2 seconds."""
        client: AsyncClient = async_client  # type: ignore[assignment]

        start = time.monotonic()
        r = await client.get("/api/v1/admin/connections/")
        elapsed = time.monotonic() - start

        assert r.status_code == 200
        assert elapsed < 2.0, f"Connection list took {elapsed:.2f}s"

    async def test_connection_create_latency(self, async_client: object) -> None:
        """POST /connections/ should respond within 2 seconds."""
        client: AsyncClient = async_client  # type: ignore[assignment]

        start = time.monotonic()
        r = await client.post(
            "/api/v1/admin/connections/",
            json={
                "name": _unique("perf-conn"),
                "host": "oracle.example.com",
                "service_name": "SVC",
                "username": "hr",
                "password": "secret",
            },
        )
        elapsed = time.monotonic() - start

        assert r.status_code == 201
        assert elapsed < 2.0, f"Connection create took {elapsed:.2f}s"

    async def test_endpoint_create_latency(self, async_client: object) -> None:
        """POST /endpoints/ should respond within 2 seconds."""
        client: AsyncClient = async_client  # type: ignore[assignment]

        # Create connection first
        r = await client.post(
            "/api/v1/admin/connections/",
            json={
                "name": _unique("perf-conn-ep"),
                "host": "oracle.example.com",
                "service_name": "SVC",
                "username": "hr",
                "password": "secret",
            },
        )
        conn_id = r.json()["id"]

        start = time.monotonic()
        r = await client.post(
            "/api/v1/admin/endpoints/",
            json={
                "name": _unique("perf-ep"),
                "path": _unique("perf-data"),
                "connection_id": conn_id,
                "sql_text": "SELECT 1 FROM dual",
                "allow_unauthenticated": True,
            },
        )
        elapsed = time.monotonic() - start

        assert r.status_code == 201
        assert elapsed < 2.0, f"Endpoint create took {elapsed:.2f}s"

    async def test_health_dashboard_latency(self, async_client: object) -> None:
        """GET /health/dashboard should respond within 3 seconds."""
        client: AsyncClient = async_client  # type: ignore[assignment]

        start = time.monotonic()
        r = await client.get("/api/v1/admin/health/dashboard")
        elapsed = time.monotonic() - start

        assert r.status_code == 200
        assert elapsed < 3.0, f"Health dashboard took {elapsed:.2f}s"

    async def test_settings_list_latency(self, async_client: object) -> None:
        """GET /settings/ should respond within 2 seconds."""
        client: AsyncClient = async_client  # type: ignore[assignment]

        start = time.monotonic()
        r = await client.get("/api/v1/admin/settings/")
        elapsed = time.monotonic() - start

        assert r.status_code == 200
        assert elapsed < 2.0, f"Settings list took {elapsed:.2f}s"


@pytest.mark.integration
class TestDataApiLatency:
    """Data endpoint response time sanity checks."""

    async def test_data_404_latency(self, async_client: object) -> None:
        """404 on non-existent data path should be fast."""
        client: AsyncClient = async_client  # type: ignore[assignment]

        start = time.monotonic()
        r = await client.get("/api/v1/data/nonexistent-path")
        elapsed = time.monotonic() - start

        assert r.status_code == 404
        assert elapsed < 1.0, f"Data 404 took {elapsed:.2f}s"

    async def test_data_auth_rejection_latency(self, async_client: object) -> None:
        """Auth rejection on a protected endpoint should be fast."""
        client: AsyncClient = async_client  # type: ignore[assignment]

        # Create protected endpoint
        r = await client.post(
            "/api/v1/admin/connections/",
            json={
                "name": _unique("perf-auth-conn"),
                "host": "oracle.example.com",
                "service_name": "SVC",
                "username": "hr",
                "password": "secret",
            },
        )
        conn_id = r.json()["id"]

        r = await client.post(
            "/api/v1/admin/auth/",
            json={"name": _unique("perf-auth"), "method_type": "bearer"},
        )
        auth_id = r.json()["id"]

        ep_path = _unique("perf-auth-data")
        r = await client.post(
            "/api/v1/admin/endpoints/",
            json={
                "name": _unique("perf-auth-ep"),
                "path": ep_path,
                "connection_id": conn_id,
                "sql_text": "SELECT 1 FROM dual",
                "auth_method_id": auth_id,
            },
        )
        assert r.status_code == 201

        # Measure auth rejection time
        start = time.monotonic()
        r = await client.get(f"/api/v1/data/{ep_path}")
        elapsed = time.monotonic() - start

        assert r.status_code == 401
        assert elapsed < 1.0, f"Auth rejection took {elapsed:.2f}s"

    async def test_snapshot_503_latency(self, async_client: object) -> None:
        """503 for missing snapshot should be fast."""
        client: AsyncClient = async_client  # type: ignore[assignment]

        r = await client.post(
            "/api/v1/admin/connections/",
            json={
                "name": _unique("perf-snap-conn"),
                "host": "oracle.example.com",
                "service_name": "SVC",
                "username": "hr",
                "password": "secret",
            },
        )
        conn_id = r.json()["id"]

        ep_path = _unique("perf-snap-data")
        r = await client.post(
            "/api/v1/admin/endpoints/",
            json={
                "name": _unique("perf-snap-ep"),
                "path": ep_path,
                "connection_id": conn_id,
                "sql_text": "SELECT 1 FROM dual",
                "data_strategy": "snapshot",
                "allow_unauthenticated": True,
            },
        )
        assert r.status_code == 201

        start = time.monotonic()
        r = await client.get(f"/api/v1/data/{ep_path}")
        elapsed = time.monotonic() - start

        assert r.status_code == 503
        assert elapsed < 1.0, f"Snapshot 503 took {elapsed:.2f}s"


@pytest.mark.integration
class TestBulkOperationPerformance:
    """Verify bulk operations don't degrade."""

    async def test_create_many_connections(self, async_client: object) -> None:
        """Creating 20 connections should complete in under 10 seconds."""
        client: AsyncClient = async_client  # type: ignore[assignment]

        start = time.monotonic()
        for i in range(20):
            r = await client.post(
                "/api/v1/admin/connections/",
                json={
                    "name": _unique(f"bulk-conn-{i}"),
                    "host": "oracle.example.com",
                    "service_name": "SVC",
                    "username": "hr",
                    "password": "secret",
                },
            )
            assert r.status_code == 201
        elapsed = time.monotonic() - start

        assert elapsed < 10.0, f"Creating 20 connections took {elapsed:.2f}s"

    async def test_list_connections_with_many(self, async_client: object) -> None:
        """Listing connections with many rows should still be fast."""
        client: AsyncClient = async_client  # type: ignore[assignment]

        start = time.monotonic()
        r = await client.get("/api/v1/admin/connections/")
        elapsed = time.monotonic() - start

        assert r.status_code == 200
        assert elapsed < 2.0, f"Listing connections took {elapsed:.2f}s"
