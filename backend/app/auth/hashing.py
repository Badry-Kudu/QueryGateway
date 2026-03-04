"""Credential hashing and random secret generation.

All password/key hashing uses bcrypt exclusively (project convention).
"""

import base64
import secrets

import bcrypt


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
