"""Admin authentication: env-seeded single-user login + JWT bearer dependency.

Phase 2 introduces a single admin account whose credentials are supplied
via ``ADMIN_USERNAME`` and ``ADMIN_PASSWORD_HASH`` (bcrypt). Logging in
mints a short-lived JWT signed with ``JWT_SECRET_KEY``. Every admin
router declares ``dependencies=[Depends(get_current_admin)]`` so an
unauthenticated or invalid request never reaches the handler.

There is no users table. Rotating the credential means redeploying with
a new ``ADMIN_PASSWORD_HASH``. If a multi-user model is ever needed the
dependency surface stays the same — only this module changes.
"""

from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.hashing import verify_password
from app.auth.jwt_utils import TokenError, verify_access_token
from app.config import settings


@dataclass(frozen=True, slots=True)
class AdminPrincipal:
    """The authenticated admin identity attached to a request."""

    username: str


# HTTPBearer (rather than OAuth2PasswordBearer) because the login route
# accepts a JSON body, not OAuth2's form-encoded password grant. Using
# OAuth2PasswordBearer here would cause FastAPI's docs to advertise an
# OAuth2 password flow that doesn't match the real contract.
# ``auto_error=False`` lets us raise our own 401 with a stable detail.
_bearer_scheme = HTTPBearer(auto_error=False)


def authenticate_admin(username: str, password: str) -> AdminPrincipal | None:
    """Verify the supplied credentials against the seeded admin.

    Returns ``AdminPrincipal`` on success, ``None`` on failure. The bcrypt
    verification is run even on a username mismatch to keep the timing
    profile constant (limits user-enumeration via response timing).
    """
    candidate_hash = settings.admin_password_hash
    password_ok = verify_password(password, candidate_hash)
    username_ok = username == settings.admin_username
    if username_ok and password_ok:
        return AdminPrincipal(username=settings.admin_username)
    return None


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),  # noqa: B008
) -> AdminPrincipal:
    """FastAPI dependency that resolves the bearer token to an AdminPrincipal.

    Raises ``HTTPException(401)`` for missing, expired, malformed, or
    otherwise invalid tokens. Apply at the router level via
    ``APIRouter(..., dependencies=[Depends(get_current_admin)])`` so
    unauthenticated traffic is rejected before any handler runs.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = verify_access_token(
            credentials.credentials,
            secret=settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    # `verify_access_token` requires sub/exp/iat to be present, but we
    # still defensively check that sub matches the configured admin in
    # case the username was rotated between issuing and verifying.
    subject = payload.get("sub")
    if not isinstance(subject, str) or subject != settings.admin_username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token subject does not match the configured admin.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return AdminPrincipal(username=subject)
