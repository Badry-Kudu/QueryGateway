"""Tests for the admin login flow — POST /api/v1/auth/login."""

from datetime import datetime

import jwt
from app.config import settings
from httpx import AsyncClient

from tests.conftest import ADMIN_TEST_PASSWORD


async def test_login_success(unauth_client: AsyncClient) -> None:
    r = await unauth_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": ADMIN_TEST_PASSWORD},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str) and body["access_token"]
    # `expires_at` round-trips as ISO-8601.
    datetime.fromisoformat(body["expires_at"].replace("Z", "+00:00"))

    # The token must carry the full claim set (sub/iat/exp). Decoding here
    # verifies the signature too, so we know the token is genuinely usable.
    payload = jwt.decode(
        body["access_token"],
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )
    assert payload["sub"] == "admin"
    assert isinstance(payload["iat"], int)
    assert isinstance(payload["exp"], int)
    assert payload["exp"] > payload["iat"]


async def test_login_wrong_password(unauth_client: AsyncClient) -> None:
    r = await unauth_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "definitely-not-the-password"},
    )
    assert r.status_code == 401
    assert "Invalid username or password" in r.json()["detail"]


async def test_login_wrong_username(unauth_client: AsyncClient) -> None:
    r = await unauth_client.post(
        "/api/v1/auth/login",
        json={"username": "not-the-admin", "password": ADMIN_TEST_PASSWORD},
    )
    assert r.status_code == 401
    assert "Invalid username or password" in r.json()["detail"]


async def test_login_missing_fields_422(unauth_client: AsyncClient) -> None:
    r = await unauth_client.post("/api/v1/auth/login", json={"username": "admin"})
    assert r.status_code == 422


async def test_login_empty_fields_422(unauth_client: AsyncClient) -> None:
    r = await unauth_client.post(
        "/api/v1/auth/login",
        json={"username": "", "password": ""},
    )
    assert r.status_code == 422


async def test_me_returns_principal(unauth_client: AsyncClient) -> None:
    """After logging in, the returned token should be accepted by /me."""
    login = await unauth_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": ADMIN_TEST_PASSWORD},
    )
    token = login.json()["access_token"]

    r = await unauth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json() == {"username": "admin"}


async def test_me_without_token_401(unauth_client: AsyncClient) -> None:
    r = await unauth_client.get("/api/v1/auth/me")
    assert r.status_code == 401
    assert r.headers.get("www-authenticate", "").lower().startswith("bearer")


async def test_me_with_garbage_token_401(unauth_client: AsyncClient) -> None:
    r = await unauth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not-a-real-jwt"},
    )
    assert r.status_code == 401
