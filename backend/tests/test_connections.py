"""Tests for connection management — service, repository, and API layer.

Integration tests (requiring PostgreSQL) are marked with @pytest.mark.integration
and run in CI where the service is available.

Unit tests exercise schema validation, crypto, and service logic in isolation.
"""

import uuid

import pytest
from app.crypto import decrypt_password, encrypt_password
from app.schemas.connection import ConnectionCreate, ConnectionResponse, ConnectionUpdate

# ── Crypto unit tests ─────────────────────────────────────────────────────────


def test_encrypt_decrypt_roundtrip() -> None:
    plaintext = "super-secret-password-123!"
    ciphertext = encrypt_password(plaintext)
    assert isinstance(ciphertext, bytes)
    assert ciphertext != plaintext.encode()
    assert decrypt_password(ciphertext) == plaintext


def test_decrypt_corrupted_bytes_raises() -> None:
    with pytest.raises(ValueError, match="Failed to decrypt"):
        decrypt_password(b"not-valid-fernet-data")


def test_encrypt_produces_different_tokens() -> None:
    """Fernet uses random IV so every call produces a distinct token."""
    p1 = encrypt_password("same-password")
    p2 = encrypt_password("same-password")
    assert p1 != p2
    assert decrypt_password(p1) == decrypt_password(p2) == "same-password"


# ── Schema validation unit tests ──────────────────────────────────────────────


def test_connection_create_requires_service_name_or_sid() -> None:
    with pytest.raises(ValueError, match="service_name or sid"):
        ConnectionCreate(
            name="test",
            host="localhost",
            username="user",
            password="pass",
            # neither service_name nor sid
        )


def test_connection_create_rejects_both_service_name_and_sid() -> None:
    with pytest.raises(ValueError, match="either service_name or sid"):
        ConnectionCreate(
            name="test",
            host="localhost",
            service_name="svc",
            sid="mysid",
            username="user",
            password="pass",
        )


def test_connection_create_valid_service_name() -> None:
    payload = ConnectionCreate(
        name="prod-oracle",
        host="oracle.example.com",
        port=1521,
        service_name="ORCLPDB",
        username="hr",
        password="secret",
    )
    assert payload.name == "prod-oracle"
    assert payload.service_name == "ORCLPDB"
    assert payload.sid is None


def test_connection_create_valid_sid() -> None:
    payload = ConnectionCreate(
        name="legacy-oracle",
        host="oracle.example.com",
        sid="ORCL",
        username="hr",
        password="secret",
    )
    assert payload.sid == "ORCL"
    assert payload.service_name is None


def test_connection_create_pool_min_le_max() -> None:
    with pytest.raises(ValueError, match="pool_min"):
        ConnectionCreate(
            name="test",
            host="localhost",
            service_name="SVC",
            username="user",
            password="pass",
            pool_min=10,
            pool_max=5,
        )


def test_connection_update_all_optional() -> None:
    payload = ConnectionUpdate()
    assert payload.name is None
    assert payload.host is None
    assert payload.password is None


def test_connection_response_has_no_password_field() -> None:
    fields = ConnectionResponse.model_fields
    assert "password" not in fields
    assert "encrypted_password" not in fields
    assert "has_password" in fields


# ── API integration tests (require PostgreSQL) ────────────────────────────────


@pytest.mark.integration
async def test_create_connection(async_client: object) -> None:
    from httpx import AsyncClient

    client: AsyncClient = async_client  # type: ignore[assignment]

    payload = {
        "name": "test-conn-create",
        "host": "oracle.example.com",
        "port": 1521,
        "service_name": "ORCLPDB",
        "username": "hr",
        "password": "secret123",
    }
    response = await client.post("/api/v1/admin/connections/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "test-conn-create"
    assert data["has_password"] is True
    assert "password" not in data
    assert "encrypted_password" not in data
    assert uuid.UUID(data["id"])


@pytest.mark.integration
async def test_create_duplicate_name_returns_409(async_client: object) -> None:
    from httpx import AsyncClient

    client: AsyncClient = async_client  # type: ignore[assignment]

    payload = {
        "name": "test-conn-dup",
        "host": "oracle.example.com",
        "service_name": "ORCLPDB",
        "username": "hr",
        "password": "secret",
    }
    r1 = await client.post("/api/v1/admin/connections/", json=payload)
    assert r1.status_code == 201
    r2 = await client.post("/api/v1/admin/connections/", json=payload)
    assert r2.status_code == 409


@pytest.mark.integration
async def test_get_connection_not_found(async_client: object) -> None:
    from httpx import AsyncClient

    client: AsyncClient = async_client  # type: ignore[assignment]

    response = await client.get(f"/api/v1/admin/connections/{uuid.uuid4()}")
    assert response.status_code == 404


@pytest.mark.integration
async def test_list_connections(async_client: object) -> None:
    from httpx import AsyncClient

    client: AsyncClient = async_client  # type: ignore[assignment]

    payload = {
        "name": "test-conn-list",
        "host": "oracle.example.com",
        "service_name": "SVC",
        "username": "scott",
        "password": "tiger",
    }
    await client.post("/api/v1/admin/connections/", json=payload)
    response = await client.get("/api/v1/admin/connections/")
    assert response.status_code == 200
    items = response.json()
    assert isinstance(items, list)
    assert any(c["name"] == "test-conn-list" for c in items)


@pytest.mark.integration
async def test_update_connection(async_client: object) -> None:
    from httpx import AsyncClient

    client: AsyncClient = async_client  # type: ignore[assignment]

    create_payload = {
        "name": "test-conn-update",
        "host": "oracle.example.com",
        "service_name": "SVC",
        "username": "scott",
        "password": "tiger",
    }
    r = await client.post("/api/v1/admin/connections/", json=create_payload)
    assert r.status_code == 201
    conn_id = r.json()["id"]

    update_payload = {"description": "Updated description", "port": 1522}
    r2 = await client.put(f"/api/v1/admin/connections/{conn_id}", json=update_payload)
    assert r2.status_code == 200
    data = r2.json()
    assert data["description"] == "Updated description"
    assert data["port"] == 1522


@pytest.mark.integration
async def test_delete_connection(async_client: object) -> None:
    from httpx import AsyncClient

    client: AsyncClient = async_client  # type: ignore[assignment]

    create_payload = {
        "name": "test-conn-delete",
        "host": "oracle.example.com",
        "service_name": "SVC",
        "username": "scott",
        "password": "tiger",
    }
    r = await client.post("/api/v1/admin/connections/", json=create_payload)
    assert r.status_code == 201
    conn_id = r.json()["id"]

    r_del = await client.delete(f"/api/v1/admin/connections/{conn_id}")
    assert r_del.status_code == 204

    r_get = await client.get(f"/api/v1/admin/connections/{conn_id}")
    assert r_get.status_code == 404


@pytest.mark.integration
async def test_test_connection_not_found(async_client: object) -> None:
    from httpx import AsyncClient

    client: AsyncClient = async_client  # type: ignore[assignment]

    response = await client.post(f"/api/v1/admin/connections/{uuid.uuid4()}/test")
    assert response.status_code == 404


@pytest.mark.integration
async def test_password_not_in_response(async_client: object) -> None:
    """Ensure password and encrypted_password are never present in any response."""
    from httpx import AsyncClient

    client: AsyncClient = async_client  # type: ignore[assignment]

    payload = {
        "name": "test-conn-secure",
        "host": "oracle.example.com",
        "service_name": "SVC",
        "username": "scott",
        "password": "do-not-expose",
    }
    r = await client.post("/api/v1/admin/connections/", json=payload)
    assert r.status_code == 201
    data = r.json()
    assert "password" not in data
    assert "encrypted_password" not in data
    assert data["has_password"] is True

    # Also check GET single
    conn_id = data["id"]
    r2 = await client.get(f"/api/v1/admin/connections/{conn_id}")
    data2 = r2.json()
    assert "password" not in data2
    assert "encrypted_password" not in data2

    # And GET list
    r3 = await client.get("/api/v1/admin/connections/")
    for item in r3.json():
        assert "password" not in item
        assert "encrypted_password" not in item
