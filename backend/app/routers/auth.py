"""Admin authentication endpoints — /api/v1/auth/*.

These routes are intentionally outside the /api/v1/admin/* prefix so
they don't get caught by the admin auth dependency that protects every
other admin route. Logging in *grants* the credential needed for those
routes; protecting login itself with the same credential would be a
chicken-and-egg.
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.admin import (
    AdminPrincipal,
    authenticate_admin,
    get_current_admin,
)
from app.auth.jwt_utils import create_access_token
from app.config import settings
from app.schemas.auth import LoginRequest, MeResponse, TokenResponse

log = structlog.get_logger()

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Admin login",
    description="Exchange admin username + password for a short-lived JWT.",
)
async def login(payload: LoginRequest) -> TokenResponse:
    principal = authenticate_admin(payload.username, payload.password)
    if principal is None:
        log.info("admin_login_failed", username=payload.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token, expires_at = create_access_token(
        subject=principal.username,
        secret=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expire_minutes=settings.jwt_access_token_expire_minutes,
    )
    log.info("admin_login_success", username=principal.username)
    return TokenResponse(access_token=token, expires_at=expires_at)


@router.get(
    "/me",
    response_model=MeResponse,
    summary="Current admin",
    description="Return the username embedded in the supplied bearer token.",
)
async def me(
    principal: AdminPrincipal = Depends(get_current_admin),
) -> MeResponse:
    return MeResponse(username=principal.username)
