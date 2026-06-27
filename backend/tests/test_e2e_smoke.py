"""Phase 7 — End-to-end smoke tests.

These tests exercise the full cross-module lifecycle:
  1. Create a connection
  2. Create an auth method (bearer)
  3. Issue a JWT token
  4. Create an endpoint linked to connection + auth method
  5. Verify the data endpoint enforces auth (401 without token)
  6. Verify data endpoint returns 404 for non-existent paths
  7. Verify endpoint deactivation hides it from /api/v1/data/*
  8. Verify schedule creation for snapshot-mode endpoints
  9. Health dashboard reflects system state

All tests use the PostgreSQL-backed test database.  Oracle connectivity
is not required — these tests validate the *admin* and *data router*
contract layers, not the SQL execution engine.
"""

import base64
import uuid

import pytest
from httpx import AsyncClient

# ── Helpers ──────────────────────────────────────────────────────────────────


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


# ── Cross-module lifecycle smoke test ────────────────────────────────────────


@pytest.mark.integration
class TestE2ELifecycleSmoke:
    """Full lifecycle: connection → auth → endpoint → schedule → data."""

    async def test_full_lifecycle(self, async_client: object) -> None:
        """Verify the complete admin workflow produces a functioning data endpoint."""
        client: AsyncClient = async_client  # type: ignore[assignment]

        # ── Step 1: Create a connection ──────────────────────────────────
        conn_name = _unique("e2e-conn")
        conn_payload = {
            "name": conn_name,
            "host": "oracle.example.com",
            "service_name": "ORCLPDB",
            "username": "hr",
            "password": "secret123",
        }
        r = await client.post("/api/v1/admin/connections/", json=conn_payload)
        assert r.status_code == 201, f"Connection create failed: {r.text}"
        conn_data = r.json()
        conn_id = conn_data["id"]
        assert conn_data["name"] == conn_name
        assert conn_data["is_active"] is True
        assert "encrypted_password" not in r.text  # credential not leaked

        # ── Step 2: Create a bearer auth method ──────────────────────────
        auth_name = _unique("e2e-bearer")
        auth_payload = {
            "name": auth_name,
            "method_type": "bearer",
            "expire_minutes": 60,
        }
        r = await client.post("/api/v1/admin/auth/", json=auth_payload)
        assert r.status_code == 201, f"Auth create failed: {r.text}"
        auth_data = r.json()
        auth_id = auth_data["id"]
        assert auth_data["method_type"] == "bearer"
        assert "signing_secret" not in r.text  # secret not leaked

        # ── Step 3: Issue a JWT ──────────────────────────────────────────
        r = await client.post(f"/api/v1/admin/auth/{auth_id}/issue-token")
        assert r.status_code == 200, f"Token issuance failed: {r.text}"
        token_data = r.json()
        jwt_token = token_data["token"]
        assert token_data["token_type"] == "bearer"
        assert "expires_at" in token_data

        # ── Step 4: Create an endpoint (live mode, with auth) ────────────
        ep_name = _unique("e2e-endpoint")
        ep_path = _unique("e2e-data")
        ep_payload = {
            "name": ep_name,
            "path": ep_path,
            "connection_id": conn_id,
            "sql_text": "SELECT * FROM employees WHERE dept_id = :dept_id",
            "param_schema": {
                "dept_id": {"type": "integer", "required": True},
            },
            "auth_method_id": auth_id,
            "data_strategy": "live",
        }
        r = await client.post("/api/v1/admin/endpoints/", json=ep_payload)
        assert r.status_code == 201, f"Endpoint create failed: {r.text}"
        ep_data = r.json()
        ep_id = ep_data["id"]
        assert ep_data["path"] == ep_path
        assert ep_data["auth_method_id"] == auth_id
        assert ep_data["data_strategy"] == "live"
        assert ep_data["is_active"] is True

        # ── Step 5: Data endpoint without auth → 401 ────────────────────
        r = await client.get(f"/api/v1/data/{ep_path}?dept_id=10")
        assert r.status_code == 401, f"Expected 401 without auth, got {r.status_code}"

        # ── Step 6: Data endpoint with valid auth → will try to execute SQL
        #            Since there is no real Oracle, the call will fail with 503
        #            (connection unavailable) or 500, but NOT 401/404.
        r = await client.get(
            f"/api/v1/data/{ep_path}?dept_id=10",
            headers={"Authorization": f"Bearer {jwt_token}"},
        )
        # Auth passed → we get a downstream error (no real Oracle connection)
        assert r.status_code in (500, 503), (
            f"Expected 500/503 (no Oracle), got {r.status_code}: {r.text}"
        )

        # ── Step 7: Deactivate endpoint → 404 ───────────────────────────
        r = await client.put(
            f"/api/v1/admin/endpoints/{ep_id}",
            json={"is_active": False},
        )
        assert r.status_code == 200
        assert r.json()["is_active"] is False

        r = await client.get(
            f"/api/v1/data/{ep_path}?dept_id=10",
            headers={"Authorization": f"Bearer {jwt_token}"},
        )
        assert r.status_code == 404, "Deactivated endpoint should return 404"

        # ── Step 8: Re-activate endpoint ─────────────────────────────────
        r = await client.put(
            f"/api/v1/admin/endpoints/{ep_id}",
            json={"is_active": True},
        )
        assert r.status_code == 200
        assert r.json()["is_active"] is True

    async def test_snapshot_mode_endpoint(self, async_client: object) -> None:
        """Snapshot-strategy endpoint returns 503 when no snapshot exists."""
        client: AsyncClient = async_client  # type: ignore[assignment]

        # Create connection
        r = await client.post(
            "/api/v1/admin/connections/",
            json={
                "name": _unique("snap-conn"),
                "host": "oracle.example.com",
                "service_name": "SVC",
                "username": "scott",
                "password": "tiger",
            },
        )
        assert r.status_code == 201
        conn_id = r.json()["id"]

        # Create snapshot endpoint (no auth for simplicity)
        ep_path = _unique("snap-data")
        r = await client.post(
            "/api/v1/admin/endpoints/",
            json={
                "name": _unique("snap-ep"),
                "path": ep_path,
                "connection_id": conn_id,
                "sql_text": "SELECT 1 FROM dual",
                "data_strategy": "snapshot",
                "allow_unauthenticated": True,
            },
        )
        assert r.status_code == 201
        ep_id = r.json()["id"]

        # Data endpoint should return 503 — no snapshot yet
        r = await client.get(f"/api/v1/data/{ep_path}")
        assert r.status_code == 503
        assert "No snapshot available" in r.json()["detail"]

        # Create a schedule for this endpoint
        r = await client.post(
            "/api/v1/admin/schedules/",
            json={
                "endpoint_id": ep_id,
                "schedule_type": "interval",
                "interval_seconds": 300,
            },
        )
        assert r.status_code == 201
        schedule_data = r.json()
        assert schedule_data["endpoint_id"] == ep_id
        assert schedule_data["is_active"] is True


# ── Auth type coverage ───────────────────────────────────────────────────────


@pytest.mark.integration
class TestE2EAuthTypes:
    """Verify all three auth types work through the data endpoint."""

    async def _create_connection_and_endpoint(
        self, client: AsyncClient, auth_id: str | None
    ) -> str:
        """Helper: create a connection + endpoint, return the data path."""
        r = await client.post(
            "/api/v1/admin/connections/",
            json={
                "name": _unique("auth-conn"),
                "host": "oracle.example.com",
                "service_name": "SVC",
                "username": "scott",
                "password": "tiger",
            },
        )
        conn_id = r.json()["id"]

        ep_path = _unique("auth-data")
        payload: dict[str, object] = {
            "name": _unique("auth-ep"),
            "path": ep_path,
            "connection_id": conn_id,
            "sql_text": "SELECT 1 FROM dual",
        }
        if auth_id is not None:
            payload["auth_method_id"] = auth_id
        else:
            # No auth method: this endpoint is deliberately public, so it must
            # opt in explicitly (M1).
            payload["allow_unauthenticated"] = True

        r = await client.post("/api/v1/admin/endpoints/", json=payload)
        assert r.status_code == 201
        return ep_path

    async def test_bearer_auth_enforced(
        self, async_client: object, unauth_client: AsyncClient
    ) -> None:
        client: AsyncClient = async_client  # type: ignore[assignment]

        # Create bearer auth
        r = await client.post(
            "/api/v1/admin/auth/",
            json={"name": _unique("bearer"), "method_type": "bearer"},
        )
        auth_id = r.json()["id"]
        ep_path = await self._create_connection_and_endpoint(client, auth_id)

        # The default `async_client` carries an admin bearer token (Phase 2);
        # the data plane has its own auth and admin tokens aren't valid
        # against it. Use `unauth_client` here to exercise the genuinely
        # no-Authorization-header path.
        r = await unauth_client.get(f"/api/v1/data/{ep_path}")
        assert r.status_code == 401
        assert "Bearer token required" in r.json()["detail"]

        # Wrong token → 401
        r = await client.get(
            f"/api/v1/data/{ep_path}",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert r.status_code == 401

    async def test_basic_auth_enforced(self, async_client: object) -> None:
        client: AsyncClient = async_client  # type: ignore[assignment]

        # Create basic auth
        r = await client.post(
            "/api/v1/admin/auth/",
            json={
                "name": _unique("basic"),
                "method_type": "basic",
                "username": "admin",
                "password": "s3cr3t",
            },
        )
        auth_id = r.json()["id"]
        ep_path = await self._create_connection_and_endpoint(client, auth_id)

        # No auth → 401
        r = await client.get(f"/api/v1/data/{ep_path}")
        assert r.status_code == 401
        assert "Basic credentials required" in r.json()["detail"]

        # Wrong password → 401
        creds = base64.b64encode(b"admin:wrong").decode()
        r = await client.get(
            f"/api/v1/data/{ep_path}",
            headers={"Authorization": f"Basic {creds}"},
        )
        assert r.status_code == 401

        # Correct credentials → should pass auth (fail downstream on Oracle)
        creds = base64.b64encode(b"admin:s3cr3t").decode()
        r = await client.get(
            f"/api/v1/data/{ep_path}",
            headers={"Authorization": f"Basic {creds}"},
        )
        assert r.status_code in (500, 503)  # auth passed, no Oracle

    async def test_api_key_auth_enforced(self, async_client: object) -> None:
        client: AsyncClient = async_client  # type: ignore[assignment]

        # Create API key auth — first via /with-key to get the key
        apikey_name = _unique("apikey")
        r = await client.post(
            "/api/v1/admin/auth/with-key",
            json={"name": apikey_name, "method_type": "api_key"},
        )
        assert r.status_code == 201
        api_key = r.json()["api_key"]

        # Look up the auth method by listing and filtering by name
        r = await client.get("/api/v1/admin/auth/")
        auth_id = next(a["id"] for a in r.json() if a["name"] == apikey_name)

        ep_path = await self._create_connection_and_endpoint(client, auth_id)

        # No auth → 401
        r = await client.get(f"/api/v1/data/{ep_path}")
        assert r.status_code == 401

        # Wrong key → 401
        r = await client.get(
            f"/api/v1/data/{ep_path}",
            headers={"X-Api-Key": "wrong_key_here"},
        )
        assert r.status_code == 401

        # Correct key → auth passes (fail downstream on Oracle)
        r = await client.get(
            f"/api/v1/data/{ep_path}",
            headers={"X-Api-Key": api_key},
        )
        assert r.status_code in (500, 503)

    async def test_no_auth_endpoint_accessible(self, async_client: object) -> None:
        """Endpoint without auth should be accessible without credentials."""
        client: AsyncClient = async_client  # type: ignore[assignment]

        ep_path = await self._create_connection_and_endpoint(client, None)

        # No auth required → should pass to query execution
        r = await client.get(f"/api/v1/data/{ep_path}")
        # No Oracle → 500/503, but NOT 401
        assert r.status_code in (500, 503)


# ── Health dashboard smoke ───────────────────────────────────────────────────


@pytest.mark.integration
class TestE2EHealthDashboard:
    """Health endpoints reflect system state correctly."""

    async def test_liveness(self, async_client: object) -> None:
        client: AsyncClient = async_client  # type: ignore[assignment]
        r = await client.get("/api/v1/admin/health/live")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    async def test_readiness(self, async_client: object) -> None:
        client: AsyncClient = async_client  # type: ignore[assignment]
        r = await client.get("/api/v1/admin/health/ready")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] in ("ok", "degraded")

    async def test_dashboard_returns_expected_fields(
        self, async_client: object
    ) -> None:
        client: AsyncClient = async_client  # type: ignore[assignment]
        r = await client.get("/api/v1/admin/health/dashboard")
        assert r.status_code == 200
        data = r.json()

        assert "overall" in data
        assert "components" in data
        assert "scheduler" in data
        assert "database" in data["components"]
        assert "connections" in data["components"]
        assert "endpoints" in data["components"]


# ── Settings cross-check ─────────────────────────────────────────────────────


@pytest.mark.integration
class TestE2ESettings:
    """Settings CRUD and validation integration."""

    async def test_list_settings(self, async_client: object) -> None:
        client: AsyncClient = async_client  # type: ignore[assignment]
        r = await client.get("/api/v1/admin/settings/")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    async def test_get_known_setting(self, async_client: object) -> None:
        client: AsyncClient = async_client  # type: ignore[assignment]
        # GET-by-key does not seed; the list endpoint is what seeds defaults.
        seed = await client.get("/api/v1/admin/settings/")
        assert seed.status_code == 200
        r = await client.get("/api/v1/admin/settings/query_timeout_seconds")
        assert r.status_code == 200
        data = r.json()
        assert data["key"] == "query_timeout_seconds"

    async def test_update_and_read_back(self, async_client: object) -> None:
        client: AsyncClient = async_client  # type: ignore[assignment]
        r = await client.put(
            "/api/v1/admin/settings/query_timeout_seconds",
            json={"value": "45"},
        )
        assert r.status_code == 200

        r = await client.get("/api/v1/admin/settings/query_timeout_seconds")
        assert r.status_code == 200
        assert r.json()["value"] == "45"

    async def test_restart_keys_endpoint(self, async_client: object) -> None:
        client: AsyncClient = async_client  # type: ignore[assignment]
        r = await client.get("/api/v1/admin/settings/restart-keys")
        assert r.status_code == 200
        keys = r.json()
        assert isinstance(keys, list)
        # log_level, cors_origins, max_job_concurrency require restart
        assert "log_level" in keys


# ── Connection CRUD cross-check ──────────────────────────────────────────────


@pytest.mark.integration
class TestE2EConnectionLifecycle:
    """Connection CRUD through the full API."""

    async def test_create_list_update_delete(self, async_client: object) -> None:
        client: AsyncClient = async_client  # type: ignore[assignment]

        # Create
        name = _unique("lifecycle-conn")
        r = await client.post(
            "/api/v1/admin/connections/",
            json={
                "name": name,
                "host": "db.example.com",
                "service_name": "PROD",
                "username": "app_user",
                "password": "p@ssw0rd",
            },
        )
        assert r.status_code == 201
        conn_id = r.json()["id"]

        # List
        r = await client.get("/api/v1/admin/connections/")
        assert r.status_code == 200
        assert any(c["id"] == conn_id for c in r.json())

        # Update
        r = await client.put(
            f"/api/v1/admin/connections/{conn_id}",
            json={"description": "Updated via E2E test"},
        )
        assert r.status_code == 200
        assert r.json()["description"] == "Updated via E2E test"

        # Delete
        r = await client.delete(f"/api/v1/admin/connections/{conn_id}")
        assert r.status_code == 204

        # Verify gone
        r = await client.get(f"/api/v1/admin/connections/{conn_id}")
        assert r.status_code == 404
