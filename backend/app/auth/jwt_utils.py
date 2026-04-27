"""JWT creation and verification utilities.

Uses PyJWT exclusively (project convention).
Every token includes `exp`, `iat`, and `sub` claims.
"""

from datetime import UTC, datetime, timedelta

import jwt
from jwt import DecodeError, ExpiredSignatureError, InvalidTokenError

_DEFAULT_ALGORITHM = "HS256"


class TokenError(Exception):
    """Raised when a token cannot be verified."""


def create_access_token(
    *,
    subject: str,
    secret: str,
    algorithm: str = _DEFAULT_ALGORITHM,
    expire_minutes: int = 60,
) -> tuple[str, datetime]:
    """Create a signed JWT access token.

    Args:
        subject:        Token subject (e.g. auth method name or principal id).
        secret:         HMAC signing secret.
        algorithm:      JWT algorithm (default HS256).
        expire_minutes: Lifetime in minutes.

    Returns:
        (encoded_token, expires_at) tuple.
    """
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=expire_minutes)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": expires_at,
    }
    token: str = jwt.encode(payload, secret, algorithm=algorithm)
    return token, expires_at


def verify_access_token(
    token: str,
    *,
    secret: str,
    algorithm: str = _DEFAULT_ALGORITHM,
) -> dict[str, object]:
    """Verify a JWT and return its decoded payload.

    The contract is intentionally strict: ``sub``, ``exp``, and ``iat``
    must all be present.  PyJWT only enforces ``exp`` when the claim is
    present in the token — which means a signed-but-claimless token
    would otherwise pass verification and authorize traffic forever.

    Args:
        token:     The encoded JWT string.
        secret:    HMAC signing secret used to verify the signature.
        algorithm: Expected algorithm (must match token header).

    Returns:
        Decoded payload dict.

    Raises:
        TokenError: If the token is expired, malformed, has an invalid
            signature, or is missing one of the required claims.
    """
    try:
        payload: dict[str, object] = jwt.decode(
            token,
            secret,
            algorithms=[algorithm],
            options={"require": ["exp", "iat", "sub"]},
        )
        return payload
    except ExpiredSignatureError as exc:
        raise TokenError("Token has expired.") from exc
    except (DecodeError, InvalidTokenError) as exc:
        raise TokenError(f"Invalid token: {exc}") from exc
