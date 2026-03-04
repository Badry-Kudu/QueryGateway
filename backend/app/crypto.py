"""Credential encryption utilities.

Uses Fernet symmetric encryption (AES-128-CBC + HMAC-SHA256).
The encryption key is injected from settings and never stored in the DB.

Usage:
    from app.crypto import encrypt_password, decrypt_password

    blob = encrypt_password("secret123")   # bytes — stored in DB
    plain = decrypt_password(blob)          # str  — passed to oracledb
"""

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


def _fernet() -> Fernet:
    """Return a Fernet instance using the configured encryption key."""
    return Fernet(settings.encryption_key.encode())


def encrypt_password(plaintext: str) -> bytes:
    """Encrypt a plaintext password for storage.

    Args:
        plaintext: The raw credential string.

    Returns:
        Fernet-encrypted bytes suitable for LargeBinary storage.
    """
    return _fernet().encrypt(plaintext.encode())


def decrypt_password(ciphertext: bytes) -> str:
    """Decrypt a stored credential for runtime use.

    Args:
        ciphertext: The Fernet-encrypted bytes from DB storage.

    Returns:
        Plaintext password string.

    Raises:
        ValueError: If decryption fails (wrong key or corrupted data).
    """
    try:
        return _fernet().decrypt(ciphertext).decode()
    except (InvalidToken, Exception) as exc:
        raise ValueError("Failed to decrypt credential — key mismatch or corrupted data") from exc
