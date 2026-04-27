"""Tests for application configuration safety guarantees."""

import pytest
from pydantic import ValidationError


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


def test_settings_build_when_required_envs_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Settings should build cleanly when all required envs are set."""
    monkeypatch.setenv("JWT_SECRET_KEY", "any-non-empty-value")
    monkeypatch.setenv(
        "ENCRYPTION_KEY",
        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
    )

    from app.config import Settings

    s = Settings(_env_file=None)
    assert s.jwt_secret_key == "any-non-empty-value"
