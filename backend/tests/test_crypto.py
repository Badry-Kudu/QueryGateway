"""Tests for credential encryption helpers."""

import pytest
from app.crypto import decrypt_password, encrypt_password


def test_encrypt_decrypt_roundtrip() -> None:
    plaintext = "s3cr3t-p@ssw0rd"
    blob = encrypt_password(plaintext)
    assert isinstance(blob, bytes)
    assert decrypt_password(blob) == plaintext


def test_decrypt_invalid_token_wrapped_as_value_error() -> None:
    """Fernet's InvalidToken must surface as ValueError with a stable message."""
    with pytest.raises(ValueError, match="Failed to decrypt credential"):
        decrypt_password(b"not-a-valid-fernet-token")


def test_decrypt_propagates_unexpected_errors() -> None:
    """Errors that are not InvalidToken must propagate untouched.

    Fernet raises TypeError when given a non-bytes/str token; the narrowed
    except clause must let that surface instead of wrapping it in ValueError.
    """
    with pytest.raises(TypeError):
        decrypt_password(None)  # type: ignore[arg-type]
