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
    """Hash a plaintext password with bcrypt. Returns the hash string.

    The 72-byte bound is enforced here too (not only at the schema boundary)
    so direct callers — offline admin-hash generation, scripts, future code
    paths — can't silently truncate past bcrypt's limit (L4, defence in depth).
    """
    validate_password_length(plaintext)
    return bcrypt.hashpw(plaintext.encode(), bcrypt.gensalt()).decode()


def verify_password(plaintext: str, hashed: str) -> bool:
    """Return True if plaintext matches the bcrypt hash.

    A plaintext longer than bcrypt's 72-byte input limit can never match a
    hash produced by ``hash_password`` (which rejects over-long input), so it
    is rejected here without calling bcrypt. This also keeps verification
    robust across bcrypt versions: bcrypt >= 5.0 *raises* on over-long input
    instead of silently truncating it, so an over-long credential arriving
    from an untrusted header — a Basic-auth password or API key, neither of
    which passes through the schema-level length check — would otherwise
    surface as a 500 rather than a clean authentication failure. The early
    return leaks nothing about stored credentials: it depends only on the
    caller-supplied input length, so the L5 constant-time property across
    usernames is preserved.
    """
    if len(plaintext.encode("utf-8")) > BCRYPT_MAX_PASSWORD_BYTES:
        return False
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
