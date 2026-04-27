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
from fastapi.security import OAuth2PasswordBearer

from app.auth.hashing import verify_password
from app.auth.jwt_utils import TokenError, verify_access_token
from app.config import settings


@dataclass(frozen=True, slots=True)
class AdminPrincipal:
    """The authenticated admin identity attached to a request."""

    username: str


# ``tokenUrl`` points clients (including FastAPI's docs) at the login route.
# ``auto_error=False`` so we can raise our own 401 with a clear detail.
_oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False,
)


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
    token: str | None = Depends(_oauth2_scheme),
) -> AdminPrincipal:
    """FastAPI dependency that resolves the bearer token to an AdminPrincipal.

    Raises ``HTTPException(401)`` for missing, expired, malformed, or
    otherwise invalid tokens. Apply at the router level via
    ``APIRouter(..., dependencies=[Depends(get_current_admin)])`` so
    unauthenticated traffic is rejected before any handler runs.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = verify_access_token(
            token,
            secret=settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    subject = payload.get("sub")
    if not isinstance(subject, str) or subject != settings.admin_username:
        # Token signed by us but not for the configured admin (e.g. after
        # a username change). Reject rather than trust the claim.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token subject does not match the configured admin.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return AdminPrincipal(username=subject)
