"""Tests for auth method management — hashing, JWT, schemas, service, API.

Integration tests (requiring PostgreSQL) are marked @pytest.mark.integration.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.auth.hashing import (
    generate_api_key,
    generate_signing_secret,
    hash_password,
    verify_password,
)
from app.auth.jwt_utils import TokenError, create_access_token, verify_access_token
from app.schemas.auth_method import AuthMethodCreate, AuthMethodResponse, AuthMethodUpdate

# ── Hashing unit tests ────────────────────────────────────────────────────────


def test_hash_and_verify_password() -> None:
    hashed = hash_password("my-secret")
    assert hashed != "my-secret"
    assert verify_password("my-secret", hashed)
    assert not verify_password("wrong", hashed)


def test_hash_produces_unique_values() -> None:
    h1 = hash_password("same")
    h2 = hash_password("same")
    assert h1 != h2  # bcrypt uses random salt


def test_generate_api_key_default_prefix() -> None:
    key = generate_api_key()
    assert key.startswith("db2api_")
    assert len(key) > 10


def test_generate_api_key_custom_prefix() -> None:
    key = generate_api_key("myapp_")
    assert key.startswith("myapp_")


def test_generate_signing_secret_length() -> None:
    secret = generate_signing_secret()
    assert len(secret) > 20


# ── JWT unit tests ────────────────────────────────────────────────────────────


def test_create_and_verify_token() -> None:
    secret = generate_signing_secret()
    token, expires_at = create_access_token(
        subject="test-user", secret=secret, expire_minutes=60
    )
    assert isinstance(token, str)
    assert expires_at > datetime.now(UTC)

    payload = verify_access_token(token, secret=secret)
    assert payload["sub"] == "test-user"
    assert "exp" in payload
    assert "iat" in payload


def test_verify_token_wrong_secret_raises() -> None:
    secret = generate_signing_secret()
    token, _ = create_access_token(subject="x", secret=secret)
    with pytest.raises(TokenError, match="Invalid token"):
        verify_access_token(token, secret="wrong-secret")


def test_verify_expired_token_raises() -> None:

    import jwt  # noqa: PLC0415

    secret = generate_signing_secret()
    now = datetime.now(UTC)
    expired_payload = {
        "sub": "x",
        "iat": now - timedelta(minutes=2),
        "exp": now - timedelta(minutes=1),
    }
    token = jwt.encode(expired_payload, secret, algorithm="HS256")
    with pytest.raises(TokenError, match="expired"):
        verify_access_token(token, secret=secret)


def test_verify_malformed_token_raises() -> None:
    secret = generate_signing_secret()
    with pytest.raises(TokenError):
        verify_access_token("not.a.jwt", secret=secret)


# ── Schema validation unit tests ──────────────────────────────────────────────


def test_bearer_create_defaults() -> None:
    payload = AuthMethodCreate(name="my-bearer", method_type="bearer")
    assert payload.algorithm == "HS256"
    assert payload.expire_minutes == 60


def test_basic_create_requires_username_and_password() -> None:
    with pytest.raises(ValueError, match="username is required"):
        AuthMethodCreate(name="my-basic", method_type="basic")


def test_basic_create_requires_password() -> None:
    with pytest.raises(ValueError, match="password is required"):
        AuthMethodCreate(name="my-basic", method_type="basic", username="admin")


def test_basic_create_valid() -> None:
    payload = AuthMethodCreate(
        name="basic-auth", method_type="basic", username="admin", password="s3cr3t"
    )
    assert payload.username == "admin"
    assert payload.password == "s3cr3t"


def test_api_key_create_defaults() -> None:
    payload = AuthMethodCreate(name="my-key", method_type="api_key")
    assert payload.key_prefix == "db2api_"


def test_auth_method_response_no_secrets() -> None:
    fields = AuthMethodResponse.model_fields
    assert "password" not in fields
    assert "password_hash" not in fields
    assert "signing_secret_enc" not in fields
    assert "key_hash" not in fields
    assert "config_json" not in fields


def test_auth_method_update_all_optional() -> None:
    payload = AuthMethodUpdate()
    assert payload.name is None
    assert payload.password is None


# ── API integration tests (require PostgreSQL) ────────────────────────────────


@pytest.mark.integration
async def test_create_bearer_method(async_client: object) -> None:
    from httpx import AsyncClient

    client: AsyncClient = async_client  # type: ignore[assignment]
    payload = {"name": "test-bearer", "method_type": "bearer", "expire_minutes": 120}
    r = await client.post("/api/v1/admin/auth/", json=payload)
    assert r.status_code == 201
    data = r.json()
    assert data["method_type"] == "bearer"
    assert data["algorithm"] == "HS256"
    assert data["expire_minutes"] == 120
    assert "signing_secret_enc" not in str(data)
    assert uuid.UUID(data["id"])


@pytest.mark.integration
async def test_create_basic_method(async_client: object) -> None:
    from httpx import AsyncClient

    client: AsyncClient = async_client  # type: ignore[assignment]
    payload = {
        "name": "test-basic",
        "method_type": "basic",
        "username": "admin",
        "password": "s3cr3t",
    }
    r = await client.post("/api/v1/admin/auth/", json=payload)
    assert r.status_code == 201
    data = r.json()
    assert data["username"] == "admin"
    assert "password" not in data
    assert "password_hash" not in data


@pytest.mark.integration
async def test_create_api_key_method(async_client: object) -> None:
    from httpx import AsyncClient

    client: AsyncClient = async_client  # type: ignore[assignment]
    payload = {"name": "test-apikey", "method_type": "api_key", "key_prefix": "test_"}
    r = await client.post("/api/v1/admin/auth/with-key", json=payload)
    assert r.status_code == 201
    data = r.json()
    assert data["api_key"].startswith("test_")
    assert "note" in data


@pytest.mark.integration
async def test_create_duplicate_name_returns_409(async_client: object) -> None:
    from httpx import AsyncClient

    client: AsyncClient = async_client  # type: ignore[assignment]
    payload = {"name": "test-dup-auth", "method_type": "bearer"}
    r1 = await client.post("/api/v1/admin/auth/", json=payload)
    assert r1.status_code == 201
    r2 = await client.post("/api/v1/admin/auth/", json=payload)
    assert r2.status_code == 409


@pytest.mark.integration
async def test_issue_token_bearer(async_client: object) -> None:
    from httpx import AsyncClient

    client: AsyncClient = async_client  # type: ignore[assignment]
    r = await client.post(
        "/api/v1/admin/auth/", json={"name": "bearer-for-token", "method_type": "bearer"}
    )
    assert r.status_code == 201
    auth_id = r.json()["id"]

    r2 = await client.post(f"/api/v1/admin/auth/{auth_id}/issue-token")
    assert r2.status_code == 200
    data = r2.json()
    assert "token" in data
    assert data["token_type"] == "bearer"
    assert "expires_at" in data


@pytest.mark.integration
async def test_issue_token_wrong_type_returns_422(async_client: object) -> None:
    from httpx import AsyncClient

    client: AsyncClient = async_client  # type: ignore[assignment]
    r = await client.post(
        "/api/v1/admin/auth/",
        json={"name": "basic-no-token", "method_type": "basic", "username": "u", "password": "p"},
    )
    assert r.status_code == 201
    auth_id = r.json()["id"]

    r2 = await client.post(f"/api/v1/admin/auth/{auth_id}/issue-token")
    assert r2.status_code == 422


@pytest.mark.integration
async def test_rotate_bearer(async_client: object) -> None:
    from httpx import AsyncClient

    client: AsyncClient = async_client  # type: ignore[assignment]
    r = await client.post(
        "/api/v1/admin/auth/", json={"name": "bearer-rotate", "method_type": "bearer"}
    )
    auth_id = r.json()["id"]

    await client.post(f"/api/v1/admin/auth/{auth_id}/issue-token")

    rot = await client.post(f"/api/v1/admin/auth/{auth_id}/rotate")
    assert rot.status_code == 200
    assert "rotated" in rot.json()["message"].lower()


@pytest.mark.integration
async def test_delete_auth_method(async_client: object) -> None:
    from httpx import AsyncClient

    client: AsyncClient = async_client  # type: ignore[assignment]
    r = await client.post(
        "/api/v1/admin/auth/", json={"name": "to-delete-auth", "method_type": "bearer"}
    )
    auth_id = r.json()["id"]

    r_del = await client.delete(f"/api/v1/admin/auth/{auth_id}")
    assert r_del.status_code == 204

    r_get = await client.get(f"/api/v1/admin/auth/{auth_id}")
    assert r_get.status_code == 404


@pytest.mark.integration
async def test_get_not_found(async_client: object) -> None:
    from httpx import AsyncClient

    client: AsyncClient = async_client  # type: ignore[assignment]
    r = await client.get(f"/api/v1/admin/auth/{uuid.uuid4()}")
    assert r.status_code == 404


@pytest.mark.integration
async def test_data_stub_returns_404(async_client: object) -> None:
    from httpx import AsyncClient

    client: AsyncClient = async_client  # type: ignore[assignment]
    r = await client.get("/api/v1/data/any/path")
    assert r.status_code == 404
    assert "No endpoint registered" in r.json()["detail"]
