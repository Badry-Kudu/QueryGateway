"""M1 — silent-public-endpoint prevention.

An endpoint with no auth method is served unauthenticated by design, but
that must now be a *deliberate* choice: the admin API rejects a create or
update that would leave an endpoint unauthenticated unless
``allow_unauthenticated`` is explicitly set, and the data plane emits a
``public_endpoint_served`` warning on every public hit.
"""

import uuid

import pytest
from app.schemas.endpoint import EndpointCreate
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from structlog.testing import capture_logs


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


# ── Schema-level guard (unit) ────────────────────────────────────────────────


def test_create_without_auth_or_optin_rejected() -> None:
    """No auth method and no explicit opt-in must be rejected at the schema."""
    with pytest.raises(ValueError, match="allow_unauthenticated"):
        EndpointCreate(
            name="t",
            path="p",
            connection_id=uuid.uuid4(),
            sql_text="SELECT 1 FROM dual",
        )


def test_create_explicit_public_allowed() -> None:
    """No auth method + explicit opt-in is a valid, deliberate public endpoint."""
    ep = EndpointCreate(
        name="t",
        path="p",
        connection_id=uuid.uuid4(),
        sql_text="SELECT 1 FROM dual",
        allow_unauthenticated=True,
    )
    assert ep.allow_unauthenticated is True


def test_create_with_auth_method_allowed() -> None:
    """Attaching an auth method satisfies the invariant without the flag."""
    ep = EndpointCreate(
        name="t",
        path="p",
        connection_id=uuid.uuid4(),
        sql_text="SELECT 1 FROM dual",
        auth_method_id=uuid.uuid4(),
    )
    assert ep.allow_unauthenticated is False


# ── API integration ──────────────────────────────────────────────────────────


async def _make_connection(client: AsyncClient) -> str:
    r = await client.post(
        "/api/v1/admin/connections/",
        json={
            "name": _unique("pub-conn"),
            "host": "oracle.example.com",
            "service_name": "SVC",
            "username": "hr",
            "password": "secret",
        },
    )
    assert r.status_code == 201
    return str(r.json()["id"])


@pytest.mark.integration
async def test_create_endpoint_no_auth_returns_422(async_client: object) -> None:
    client: AsyncClient = async_client  # type: ignore[assignment]
    conn_id = await _make_connection(client)

    r = await client.post(
        "/api/v1/admin/endpoints/",
        json={
            "name": _unique("pub-ep"),
            "path": _unique("pub-data"),
            "connection_id": conn_id,
            "sql_text": "SELECT 1 FROM dual",
            # No auth_method_id and allow_unauthenticated defaults to False.
        },
    )
    assert r.status_code == 422
    body = r.text
    assert "allow_unauthenticated" in body


@pytest.mark.integration
async def test_create_explicit_public_endpoint_201(async_client: object) -> None:
    client: AsyncClient = async_client  # type: ignore[assignment]
    conn_id = await _make_connection(client)

    r = await client.post(
        "/api/v1/admin/endpoints/",
        json={
            "name": _unique("pub-ep"),
            "path": _unique("pub-data"),
            "connection_id": conn_id,
            "sql_text": "SELECT 1 FROM dual",
            "allow_unauthenticated": True,
        },
    )
    assert r.status_code == 201
    assert r.json()["allow_unauthenticated"] is True


@pytest.mark.integration
async def test_update_detaching_auth_without_optin_returns_422(
    async_client: object,
) -> None:
    """Removing the auth method without opting into public access is rejected."""
    client: AsyncClient = async_client  # type: ignore[assignment]
    conn_id = await _make_connection(client)

    # Create a protected endpoint.
    r = await client.post(
        "/api/v1/admin/auth/",
        json={"name": _unique("pub-auth"), "method_type": "bearer"},
    )
    auth_id = r.json()["id"]
    r = await client.post(
        "/api/v1/admin/endpoints/",
        json={
            "name": _unique("pub-ep"),
            "path": _unique("pub-data"),
            "connection_id": conn_id,
            "sql_text": "SELECT 1 FROM dual",
            "auth_method_id": auth_id,
        },
    )
    assert r.status_code == 201
    ep_id = r.json()["id"]

    # Detach the auth method without opting into public access → 422.
    r = await client.put(
        f"/api/v1/admin/endpoints/{ep_id}",
        json={"auth_method_id": None},
    )
    assert r.status_code == 422

    # Detaching while opting in is allowed.
    r = await client.put(
        f"/api/v1/admin/endpoints/{ep_id}",
        json={"auth_method_id": None, "allow_unauthenticated": True},
    )
    assert r.status_code == 200
    assert r.json()["allow_unauthenticated"] is True


@pytest.mark.integration
async def test_public_endpoint_serves_and_logs_warning(
    async_client: object, unauth_client: AsyncClient
) -> None:
    """An explicitly public endpoint is served with NO credentials and emits a
    fully-populated public_endpoint_served audit event."""
    admin: AsyncClient = async_client  # type: ignore[assignment]
    conn_id = await _make_connection(admin)

    ep_path = _unique("pub-data")
    r = await admin.post(
        "/api/v1/admin/endpoints/",
        json={
            "name": _unique("pub-ep"),
            "path": ep_path,
            "connection_id": conn_id,
            "sql_text": "SELECT 1 FROM dual",
            "data_strategy": "snapshot",
            "allow_unauthenticated": True,
        },
    )
    assert r.status_code == 201

    with capture_logs() as logs:
        # unauth_client carries no Authorization header — proves true public access.
        resp = await unauth_client.get(f"/api/v1/data/{ep_path}")

    # Served (reached the snapshot path → 503 "no snapshot yet"), not auth-blocked.
    assert resp.status_code == 503
    warnings = [e for e in logs if e.get("event") == "public_endpoint_served"]
    assert warnings, f"expected a public_endpoint_served warning, got {logs}"
    assert warnings[0]["endpoint"] == ep_path
    assert warnings[0]["status"] == 503
    assert warnings[0]["user"] == "anonymous"
    assert warnings[0]["log_level"] == "warning"


@pytest.mark.integration
async def test_deleting_auth_method_default_denies_endpoint(
    async_client: object, unauth_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Deleting an auth method that an endpoint references (FK ondelete=SET NULL)
    must NOT make the endpoint public — it default-denies with 401. Closes the
    M1 side-channel where a protected endpoint could silently become public."""
    admin: AsyncClient = async_client  # type: ignore[assignment]
    conn_id = await _make_connection(admin)

    r = await admin.post(
        "/api/v1/admin/auth/",
        json={"name": _unique("orphan-auth"), "method_type": "bearer"},
    )
    auth_id = r.json()["id"]
    ep_path = _unique("orphan-data")
    r = await admin.post(
        "/api/v1/admin/endpoints/",
        json={
            "name": _unique("orphan-ep"),
            "path": ep_path,
            "connection_id": conn_id,
            "sql_text": "SELECT 1 FROM dual",
            "data_strategy": "snapshot",
            "auth_method_id": auth_id,
        },
    )
    assert r.status_code == 201

    # Delete the auth method → the FK ondelete=SET NULL orphans the endpoint.
    r = await admin.delete(f"/api/v1/admin/auth/{auth_id}")
    assert r.status_code == 204
    # The shared test session caches the endpoint with its old auth_method_id;
    # drop the cache so the next read reflects the DB-side SET NULL (production
    # opens a fresh session per request).
    db_session.expire_all()

    with capture_logs() as logs:
        resp = await unauth_client.get(f"/api/v1/data/{ep_path}")

    assert resp.status_code == 401  # default-deny, NOT served publicly
    denials = [e for e in logs if e.get("event") == "unauthenticated_endpoint_denied"]
    assert denials, f"expected unauthenticated_endpoint_denied, got {logs}"
    # The deny event must be self-contained for audit (§3.5).
    assert denials[0]["endpoint"] == ep_path
    assert denials[0]["status"] == 401
    assert denials[0]["user"] == "anonymous"
    assert "duration_ms" in denials[0]
    assert not any(e.get("event") == "public_endpoint_served" for e in logs)
