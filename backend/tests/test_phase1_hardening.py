"""Phase 1 application-layer hardening: L1–L5 (and config M3 lives in test_config).

Covers:
- L1  API keys accepted only via the X-Api-Key header (no query-param fallback).
- L2  structlog redaction processor masks sensitive keys.
- L3  interactive API docs disabled when APP_ENV=production.
- L4  password inputs bounded to bcrypt's 72-byte limit at the schema boundary.
- L5  data-plane Basic auth compares the username in constant time.
"""

import uuid

import pytest
from app.auth.hashing import (
    BCRYPT_MAX_PASSWORD_BYTES,
    hash_password,
    verify_password,
)
from app.logging_config import redact_sensitive
from app.repositories.auth_method import AuthMethodRepository
from app.schemas.auth import LoginRequest
from app.schemas.auth_method import AuthMethodCreate
from app.services.auth_method import AuthMethodService
from httpx import AsyncClient
from pydantic import ValidationError


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


# ── L1: API key header-only ──────────────────────────────────────────────────


@pytest.mark.integration
async def test_api_key_query_param_no_longer_authenticates(async_client: object) -> None:
    client: AsyncClient = async_client  # type: ignore[assignment]

    # Connection
    r = await client.post(
        "/api/v1/admin/connections/",
        json={
            "name": _unique("l1-conn"),
            "host": "oracle.example.com",
            "service_name": "SVC",
            "username": "hr",
            "password": "secret",
        },
    )
    conn_id = r.json()["id"]

    # API key auth method — capture the one-time plaintext key.
    r = await client.post(
        "/api/v1/admin/auth/with-key",
        json={"name": _unique("l1-key"), "method_type": "api_key"},
    )
    assert r.status_code == 201
    plaintext_key = r.json()["api_key"]
    methods = (await client.get("/api/v1/admin/auth/")).json()
    auth_id = next(m["id"] for m in methods if m["key_prefix"])

    # Snapshot endpoint so a successful auth lands on the 503 "no snapshot"
    # path rather than attempting a real Oracle query.
    ep_path = _unique("l1-data")
    r = await client.post(
        "/api/v1/admin/endpoints/",
        json={
            "name": _unique("l1-ep"),
            "path": ep_path,
            "connection_id": conn_id,
            "sql_text": "SELECT 1 FROM dual",
            "data_strategy": "snapshot",
            "auth_method_id": auth_id,
        },
    )
    assert r.status_code == 201

    # Query-string key must NOT authenticate any more — and the 401 guidance
    # points only at the header.
    r = await client.get(f"/api/v1/data/{ep_path}?api_key={plaintext_key}")
    assert r.status_code == 401
    detail = r.json()["detail"]
    assert "X-Api-Key" in detail
    assert "query" not in detail.lower()

    # Header key still authenticates (reaches the snapshot path → 503).
    r = await client.get(f"/api/v1/data/{ep_path}", headers={"X-Api-Key": plaintext_key})
    assert r.status_code == 503

    # Wrong header key is rejected.
    r = await client.get(f"/api/v1/data/{ep_path}", headers={"X-Api-Key": "wrong"})
    assert r.status_code == 401


# ── L2: log redaction ────────────────────────────────────────────────────────


def test_redact_sensitive_masks_known_keys() -> None:
    event = {
        "event": "thing_happened",
        "password": "hunter2",
        "secret": "s3cr3t",
        "token": "abc.def",
        "api_key": "db2api_xyz",
        "key": "raw",
        "Authorization": "Bearer abc",
        "signing_secret": "ss",
    }
    out = redact_sensitive(None, "info", dict(event))
    for k in ("password", "secret", "token", "api_key", "key", "Authorization", "signing_secret"):
        assert out[k] == "***REDACTED***", f"{k} not redacted"
    assert out["event"] == "thing_happened"


def test_redact_sensitive_preserves_mandatory_fields() -> None:
    event = {
        "request_id": "rid-1",
        "user": "alice",
        "endpoint": "/api/v1/data/x",
        "status": 200,
        "duration_ms": 12.3,
        "event": "data_endpoint_request",
        # scheduler fields
        "job_id": "j1",
        "run_id": "r1",
        "row_count": 5,
        "success": True,
        # near-miss names that must NOT be redacted (exact match only)
        "key_prefix": "db2api_",
    }
    out = redact_sensitive(None, "info", dict(event))
    assert out == event  # untouched


# ── L3: docs disabled in production ──────────────────────────────────────────


def test_docs_disabled_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.main as main
    from app.config import settings

    # _docs_urls reads the same settings singleton imported into app.main.
    monkeypatch.setattr(settings, "app_env", "production")
    urls = main._docs_urls()
    assert urls == {"docs_url": None, "redoc_url": None, "openapi_url": None}


def test_docs_enabled_outside_production(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.main as main
    from app.config import settings

    monkeypatch.setattr(settings, "app_env", "development")
    urls = main._docs_urls()
    assert urls["docs_url"] == "/api/docs"
    assert urls["openapi_url"] == "/api/openapi.json"


# ── L4: password byte-length bound ───────────────────────────────────────────


def test_login_password_overlength_rejected() -> None:
    with pytest.raises(ValidationError):
        LoginRequest(username="admin", password="a" * (BCRYPT_MAX_PASSWORD_BYTES + 1))


def test_login_password_at_limit_accepted() -> None:
    req = LoginRequest(username="admin", password="a" * BCRYPT_MAX_PASSWORD_BYTES)
    assert len(req.password.encode()) == BCRYPT_MAX_PASSWORD_BYTES


def test_basic_auth_password_overlength_rejected() -> None:
    with pytest.raises(ValidationError):
        AuthMethodCreate(
            name="x",
            method_type="basic",
            username="u",
            password="a" * (BCRYPT_MAX_PASSWORD_BYTES + 1),
        )


def test_multibyte_password_bounded_by_bytes_not_chars() -> None:
    # 'é' is 2 bytes in UTF-8; 37 of them = 74 bytes > 72 even though 37 < 72 chars.
    with pytest.raises(ValidationError):
        LoginRequest(username="admin", password="é" * 37)


def test_verify_password_overlength_returns_false_not_raises() -> None:
    """An over-72-byte plaintext can never match a hash we created (hash_password
    rejects it), so verification must return False — and must NOT raise. bcrypt
    >= 5.0 raises on over-long input, so without the guard in verify_password an
    over-long credential arriving from an untrusted header (Basic-auth password
    or API key, which bypass the schema-level length check) would surface as a
    500 instead of a clean authentication failure."""
    stored = hash_password("correct-horse")
    assert verify_password("correct-horse", stored) is True
    assert verify_password("wrong", stored) is False
    # Over bcrypt's 72-byte limit: must return False, must not raise.
    assert verify_password("a" * (BCRYPT_MAX_PASSWORD_BYTES + 1), stored) is False
    assert verify_password("a" * 500, stored) is False


@pytest.mark.integration
async def test_login_overlength_password_returns_422(async_client: object) -> None:
    client: AsyncClient = async_client  # type: ignore[assignment]
    r = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "a" * 200},
    )
    assert r.status_code == 422


# ── L5: constant-time username comparison in verify_basic ────────────────────


@pytest.mark.integration
async def test_verify_basic_correctness(db_session: object) -> None:
    """verify_basic returns the right answer for every credential combination."""
    svc = AuthMethodService(AuthMethodRepository(db_session))  # type: ignore[arg-type]
    response, _ = await svc.create_auth_method(
        AuthMethodCreate(
            name=_unique("l5-basic"),
            method_type="basic",
            username="alice",
            password="correct-horse",
        )
    )
    auth_id = response.id

    assert await svc.verify_basic(auth_id, "alice", "correct-horse") is True
    assert await svc.verify_basic(auth_id, "alice", "wrong") is False
    assert await svc.verify_basic(auth_id, "mallory", "correct-horse") is False
    assert await svc.verify_basic(auth_id, "mallory", "wrong") is False
    # An over-72-byte password must fail cleanly (False), not raise: bcrypt
    # >= 5.0 raises on over-long input and Basic-auth bypasses the schema bound.
    assert await svc.verify_basic(auth_id, "alice", "a" * 200) is False


@pytest.mark.integration
async def test_verify_basic_no_early_return_on_username_mismatch(
    db_session: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The bcrypt check must run even when the username does not match (L5),
    so an attacker can't enumerate usernames via response timing."""
    from app.auth.hashing import verify_password as real

    calls = {"n": 0}

    def spy(plaintext: str, hashed: str) -> bool:
        calls["n"] += 1
        return real(plaintext, hashed)

    # Patch the name as used inside the service module (string form keeps mypy
    # strict happy — the symbol isn't re-exported).
    monkeypatch.setattr("app.services.auth_method.verify_password", spy)

    svc = AuthMethodService(AuthMethodRepository(db_session))  # type: ignore[arg-type]
    response, _ = await svc.create_auth_method(
        AuthMethodCreate(
            name=_unique("l5-timing"),
            method_type="basic",
            username="alice",
            password="correct-horse",
        )
    )
    calls["n"] = 0  # reset after setup (create does not call verify_password)

    await svc.verify_basic(response.id, "definitely-not-alice", "whatever")
    assert calls["n"] == 1, "verify_password must run despite the username mismatch"
