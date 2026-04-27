"""Verify every admin router rejects requests without a valid bearer token.

These tests are the regression guard for the Phase 2 critical-security
finding: before this phase, /api/v1/admin/* was fully unauthenticated.
"""

import time

import jwt
import pytest
from app.config import settings
from httpx import AsyncClient

# Routes representative of each admin router.  GET-only paths are picked
# so the assertions don't depend on a request body.
_ADMIN_GET_PATHS = [
    "/api/v1/admin/connections/",
    "/api/v1/admin/auth/",
    "/api/v1/admin/endpoints/",
    "/api/v1/admin/schedules/",
    "/api/v1/admin/settings/",
    "/api/v1/admin/health/dashboard",
]


@pytest.mark.parametrize("path", _ADMIN_GET_PATHS)
async def test_admin_route_without_token_returns_401(
    unauth_client: AsyncClient, path: str
) -> None:
    r = await unauth_client.get(path)
    assert r.status_code == 401, f"{path} should require auth"
    assert r.headers.get("www-authenticate", "").lower().startswith("bearer")


@pytest.mark.parametrize("path", _ADMIN_GET_PATHS)
async def test_admin_route_with_valid_token_passes_auth(
    async_client: AsyncClient, path: str
) -> None:
    """The auto-authenticated `async_client` should clear the auth gate.

    The route may still return 200/404/etc. depending on the resource —
    we only assert it didn't 401.
    """
    r = await async_client.get(path)
    assert r.status_code != 401, (
        f"{path} unexpectedly rejected a valid admin token: {r.text}"
    )


@pytest.mark.parametrize("path", _ADMIN_GET_PATHS)
async def test_admin_route_with_expired_token_returns_401(
    unauth_client: AsyncClient, path: str
) -> None:
    expired = jwt.encode(
        {
            "sub": settings.admin_username,
            "iat": int(time.time()) - 7200,
            "exp": int(time.time()) - 3600,
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    r = await unauth_client.get(
        path, headers={"Authorization": f"Bearer {expired}"}
    )
    assert r.status_code == 401


@pytest.mark.parametrize("path", _ADMIN_GET_PATHS)
async def test_admin_route_with_wrong_secret_returns_401(
    unauth_client: AsyncClient, path: str
) -> None:
    """A token signed with a different secret must be rejected."""
    forged = jwt.encode(
        {
            "sub": settings.admin_username,
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
        },
        "an-attacker-controlled-secret-32-chars-long",
        algorithm=settings.jwt_algorithm,
    )
    r = await unauth_client.get(
        path, headers={"Authorization": f"Bearer {forged}"}
    )
    assert r.status_code == 401


@pytest.mark.parametrize("path", _ADMIN_GET_PATHS)
async def test_admin_route_with_wrong_subject_returns_401(
    unauth_client: AsyncClient, path: str
) -> None:
    """A correctly-signed token whose `sub` isn't the admin must be rejected."""
    impostor = jwt.encode(
        {
            "sub": "someone-else",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    r = await unauth_client.get(
        path, headers={"Authorization": f"Bearer {impostor}"}
    )
    assert r.status_code == 401


# ── Probes stay public ──────────────────────────────────────────────────────


async def test_health_live_is_public(unauth_client: AsyncClient) -> None:
    """Liveness probes must be reachable without auth (orchestrators)."""
    r = await unauth_client.get("/api/v1/admin/health/live")
    assert r.status_code == 200


async def test_health_ready_is_public(unauth_client: AsyncClient) -> None:
    """Readiness probes must be reachable without auth (load balancers)."""
    r = await unauth_client.get("/api/v1/admin/health/ready")
    assert r.status_code in (200, 503)
