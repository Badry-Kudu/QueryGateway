"""Credential hashing and random secret generation.

All password/key hashing uses bcrypt exclusively (project convention).
"""

import base64
import secrets

import bcrypt

# bcrypt only consumes the first 72 bytes of its input and silently ignores
# the rest. Accepting a longer password would mean the ignored tail
# contributes nothing to the hash — a silent weakening — so passwords are
# bounded at this limit at the schema boundary (L4).
BCRYPT_MAX_PASSWORD_BYTES = 72


def validate_password_length(plaintext: str) -> str:
    """Reject passwords longer than bcrypt's 72-byte input limit.

    Raises ``ValueError`` (surfaced as a 422 at the schema boundary). The
    limit is measured in UTF-8 *bytes*, not characters, because that is what
    bcrypt truncates on.
    """
    if len(plaintext.encode("utf-8")) > BCRYPT_MAX_PASSWORD_BYTES:
        raise ValueError(
            f"Password must be at most {BCRYPT_MAX_PASSWORD_BYTES} bytes long "
            "(bcrypt ignores any input beyond 72 bytes)."
        )
    return plaintext


def hash_password(plaintext: str) -> str:
    """Hash a plaintext password with bcrypt. Returns the hash string."""
    return bcrypt.hashpw(plaintext.encode(), bcrypt.gensalt()).decode()


def verify_password(plaintext: str, hashed: str) -> bool:
    """Return True if plaintext matches the bcrypt hash."""
    return bcrypt.checkpw(plaintext.encode(), hashed.encode())


def generate_api_key(prefix: str = "db2api_") -> str:
    """Generate a cryptographically secure API key with an optional prefix.

    The key body is 32 URL-safe random bytes (43 chars), giving ~192 bits
    of entropy.

    Returns:
        Plaintext API key — shown once, never stored in plain text.
    """
    body = secrets.token_urlsafe(32)
    return f"{prefix}{body}"


def generate_signing_secret(n_bytes: int = 32) -> str:
    """Generate a random signing secret for JWT (returned as base64 string)."""
    return base64.urlsafe_b64encode(secrets.token_bytes(n_bytes)).decode()
