"""Tests for application configuration safety guarantees."""

import pytest
from pydantic import ValidationError

# Valid Fernet key (urlsafe-base64-encoded 32 zero bytes) — safe for tests.
_VALID_FERNET_KEY = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
# 40 chars — comfortably above the min_length=32 requirement.
_VALID_JWT_KEY = "test-secret-key-do-not-use-in-production"


def test_jwt_secret_key_required(monkeypatch: pytest.MonkeyPatch) -> None:
    """Settings must fail to build when JWT_SECRET_KEY is unset."""
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)

    from app.config import Settings

    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)

    assert any(
        err["loc"] == ("jwt_secret_key",) and err["type"] == "missing"
        for err in exc_info.value.errors()
    )


def test_jwt_secret_key_rejects_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """An empty JWT_SECRET_KEY must be rejected (would yield forgeable tokens)."""
    monkeypatch.setenv("JWT_SECRET_KEY", "")
    monkeypatch.setenv("ENCRYPTION_KEY", _VALID_FERNET_KEY)

    from app.config import Settings

    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)

    assert any(
        err["loc"] == ("jwt_secret_key",) for err in exc_info.value.errors()
    )


def test_jwt_secret_key_rejects_too_short(monkeypatch: pytest.MonkeyPatch) -> None:
    """JWT_SECRET_KEY shorter than 32 characters must be rejected."""
    monkeypatch.setenv("JWT_SECRET_KEY", "short-key")
    monkeypatch.setenv("ENCRYPTION_KEY", _VALID_FERNET_KEY)

    from app.config import Settings

    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)

    assert any(
        err["loc"] == ("jwt_secret_key",) for err in exc_info.value.errors()
    )


def test_encryption_key_required(monkeypatch: pytest.MonkeyPatch) -> None:
    """Settings must fail to build when ENCRYPTION_KEY is unset."""
    monkeypatch.delenv("ENCRYPTION_KEY", raising=False)

    from app.config import Settings

    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)

    assert any(
        err["loc"] == ("encryption_key",) and err["type"] == "missing"
        for err in exc_info.value.errors()
    )


def test_encryption_key_rejects_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """Empty ENCRYPTION_KEY must be rejected by the Fernet validator."""
    monkeypatch.setenv("JWT_SECRET_KEY", _VALID_JWT_KEY)
    monkeypatch.setenv("ENCRYPTION_KEY", "")

    from app.config import Settings

    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)

    assert any(
        err["loc"] == ("encryption_key",) for err in exc_info.value.errors()
    )


def test_encryption_key_rejects_malformed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Non-Fernet ENCRYPTION_KEY must fail at startup, not on first decrypt."""
    monkeypatch.setenv("JWT_SECRET_KEY", _VALID_JWT_KEY)
    monkeypatch.setenv("ENCRYPTION_KEY", "not-a-real-fernet-key")

    from app.config import Settings

    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)

    assert any(
        err["loc"] == ("encryption_key",) for err in exc_info.value.errors()
    )


def test_settings_build_when_required_envs_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Settings should build cleanly when all required envs are set."""
    monkeypatch.setenv("JWT_SECRET_KEY", _VALID_JWT_KEY)
    monkeypatch.setenv("ENCRYPTION_KEY", _VALID_FERNET_KEY)

    from app.config import Settings

    s = Settings(_env_file=None)
    assert s.jwt_secret_key == _VALID_JWT_KEY
