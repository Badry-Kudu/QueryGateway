"""Dynamic data endpoint namespace — /api/v1/data/*.

Phase 3: Auth enforcement infrastructure is wired here.
Phase 4: Dynamic endpoint resolution and SQL execution will be added.

Every request to /api/v1/data/* is subject to per-endpoint auth verification
and access logging.  Unauthenticated or unauthorized requests are rejected
before any SQL is executed.
"""

import time
import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models.access_log import AccessLog
from app.repositories.auth_method import AuthMethodRepository
from app.services.auth_method import AuthMethodService

log = structlog.get_logger()

router = APIRouter(prefix="/api/v1/data", tags=["data"])


async def _write_access_log(
    db: AsyncSession,
    *,
    request: Request,
    path: str,
    status_code: int,
    duration_ms: float,
    principal: str | None = None,
    endpoint_id: uuid.UUID | None = None,
) -> None:
    """Append an access log row.  Errors are swallowed so they never
    interfere with the response already sent to the client."""
    try:
        request_id = str(
            request.headers.get("X-Request-ID", "")
            or request.state.__dict__.get("request_id", "")
        )
        log_entry = AccessLog(
            endpoint_id=endpoint_id,
            path=path,
            method=request.method,
            principal=principal,
            remote_ip=request.client.host if request.client else None,
            status_code=status_code,
            duration_ms=duration_ms,
            request_id=request_id,
        )
        db.add(log_entry)
        await db.flush()
        await db.commit()
    except Exception as exc:  # noqa: BLE001
        log.warning("access_log_write_failed", error=str(exc))


async def _enforce_auth(
    request: Request,
    auth_method_id: uuid.UUID,
    db: AsyncSession,
) -> str:
    """Verify the incoming request against the configured auth method.

    Returns the authenticated principal identifier.

    Raises:
        HTTPException 401: if credentials are missing or invalid.
    """
    svc = AuthMethodService(AuthMethodRepository(db))
    auth_method = await svc.get_auth_method(auth_method_id)
    if auth_method is None or not auth_method.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication configuration is unavailable.",
        )

    method_type = auth_method.method_type
    authorization = request.headers.get("Authorization", "")

    # ── Bearer ────────────────────────────────────────────────────────────
    if method_type == "bearer":
        if not authorization.lower().startswith("bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Bearer token required.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token = authorization[7:]
        principal = await svc.verify_bearer(auth_method_id, token)
        if principal is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return principal

    # ── Basic ─────────────────────────────────────────────────────────────
    if method_type == "basic":
        import base64  # noqa: PLC0415

        if not authorization.lower().startswith("basic "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Basic credentials required.",
                headers={"WWW-Authenticate": "Basic"},
            )
        try:
            decoded = base64.b64decode(authorization[6:]).decode()
            username, _, password = decoded.partition(":")
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Malformed Basic credentials.",
            ) from exc
        ok = await svc.verify_basic(auth_method_id, username, password)
        if not ok:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password.",
                headers={"WWW-Authenticate": "Basic"},
            )
        return username

    # ── API Key ───────────────────────────────────────────────────────────
    if method_type == "api_key":
        api_key = (
            request.headers.get("X-Api-Key")
            or request.query_params.get("api_key")
            or ""
        )
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key required (X-Api-Key header or ?api_key= query param).",
            )
        ok = await svc.verify_api_key(auth_method_id, api_key)
        if not ok:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key.",
            )
        return "api_key"

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unsupported auth method type.",
    )


@router.get(
    "/{full_path:path}",
    summary="Dynamic data endpoint (Phase 4)",
    description=(
        "Placeholder for dynamic endpoint resolution. "
        "Full SQL execution and result serving is implemented in Phase 4. "
        "Auth enforcement infrastructure is active."
    ),
    include_in_schema=True,
)
async def data_endpoint(
    full_path: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Phase 3 stub: returns 404 with diagnostic info.

    Phase 4 will replace this with dynamic endpoint lookup and SQL execution.
    Access logging is written for all requests hitting this namespace.
    """
    start = time.monotonic()

    await _write_access_log(
        db,
        request=request,
        path=f"/api/v1/data/{full_path}",
        status_code=404,
        duration_ms=(time.monotonic() - start) * 1000,
    )

    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "detail": f"No endpoint registered at /api/v1/data/{full_path}. "
            "Endpoints are created and published via the API Creation Wizard (Phase 4)."
        },
    )
