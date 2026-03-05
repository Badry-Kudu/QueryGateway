"""Dynamic data endpoint namespace — /api/v1/data/*.

Phase 3: Auth enforcement infrastructure.
Phase 4: Dynamic endpoint resolution and SQL execution.

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
from app.repositories.connection import ConnectionRepository
from app.repositories.endpoint import EndpointRepository
from app.services.auth_method import AuthMethodService
from app.sql.executor import SqlExecutionError, execute_query

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


def _apply_column_map(
    rows: list[dict[str, object]], column_map: dict[str, object]
) -> list[dict[str, object]]:
    """Rename columns in result rows based on the endpoint's column_map."""
    if not column_map:
        return rows
    mapped: list[dict[str, object]] = []
    for row in rows:
        new_row: dict[str, object] = {}
        for key, value in row.items():
            output_key = column_map.get(key)
            if isinstance(output_key, str):
                new_row[output_key] = value
            else:
                new_row[key] = value
        mapped.append(new_row)
    return mapped


def _coerce_param(value: str, param_type: str) -> object:
    """Coerce a query string value to the expected type."""
    if param_type == "integer":
        return int(value)
    if param_type == "float":
        return float(value)
    if param_type == "boolean":
        return value.lower() in ("true", "1", "yes")
    return value


@router.get(
    "/{full_path:path}",
    summary="Dynamic data endpoint",
    description=(
        "Resolve the endpoint by path, enforce auth, execute SQL, and return "
        "data.  Supports live query execution against Oracle connections."
    ),
    include_in_schema=True,
)
async def data_endpoint(
    full_path: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Dynamic endpoint lookup, auth enforcement, and SQL execution."""
    start = time.monotonic()
    path = full_path.strip("/").lower()
    principal: str | None = None
    endpoint_id: uuid.UUID | None = None

    try:
        # Look up endpoint by path
        repo = EndpointRepository(db)
        ep = await repo.get_by_path(path)

        if ep is None:
            duration_ms = (time.monotonic() - start) * 1000
            await _write_access_log(
                db,
                request=request,
                path=f"/api/v1/data/{full_path}",
                status_code=404,
                duration_ms=duration_ms,
            )
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "detail": f"No endpoint registered at /api/v1/data/{full_path}."
                },
            )

        endpoint_id = ep.id

        # Check endpoint is active
        if not ep.is_active:
            duration_ms = (time.monotonic() - start) * 1000
            await _write_access_log(
                db,
                request=request,
                path=f"/api/v1/data/{full_path}",
                status_code=404,
                duration_ms=duration_ms,
                endpoint_id=endpoint_id,
            )
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"detail": "Endpoint is not active."},
            )

        # Enforce auth if configured
        if ep.auth_method_id is not None:
            principal = await _enforce_auth(request, ep.auth_method_id, db)

        # Build query parameters from request query string
        params: dict[str, object] = {}
        param_schema = ep.param_schema_json or {}

        for param_name, descriptor in param_schema.items():
            if not isinstance(descriptor, dict):
                continue
            raw_value = request.query_params.get(param_name)
            param_type = descriptor.get("type", "string")
            required = descriptor.get("required", True)
            default = descriptor.get("default")

            if raw_value is not None:
                try:
                    params[param_name] = _coerce_param(
                        raw_value, str(param_type)
                    )
                except (ValueError, TypeError) as exc:
                    duration_ms = (time.monotonic() - start) * 1000
                    await _write_access_log(
                        db,
                        request=request,
                        path=f"/api/v1/data/{full_path}",
                        status_code=422,
                        duration_ms=duration_ms,
                        principal=principal,
                        endpoint_id=endpoint_id,
                    )
                    return JSONResponse(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        content={
                            "detail": (
                                f"Invalid value for parameter '{param_name}': {exc}"
                            )
                        },
                    )
            elif default is not None:
                params[param_name] = default
            elif required:
                duration_ms = (time.monotonic() - start) * 1000
                await _write_access_log(
                    db,
                    request=request,
                    path=f"/api/v1/data/{full_path}",
                    status_code=422,
                    duration_ms=duration_ms,
                    principal=principal,
                    endpoint_id=endpoint_id,
                )
                return JSONResponse(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    content={
                        "detail": f"Required parameter '{param_name}' is missing."
                    },
                )

        # Get the connection
        conn_repo = ConnectionRepository(db)
        connection = await conn_repo.get_by_id(ep.connection_id)
        if connection is None or not connection.is_active:
            duration_ms = (time.monotonic() - start) * 1000
            await _write_access_log(
                db,
                request=request,
                path=f"/api/v1/data/{full_path}",
                status_code=503,
                duration_ms=duration_ms,
                principal=principal,
                endpoint_id=endpoint_id,
            )
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"detail": "Data source connection is unavailable."},
            )

        # Execute SQL
        try:
            columns, rows, query_duration_ms = await execute_query(
                connection=connection,
                sql=ep.sql_text,
                params=params,
            )
        except SqlExecutionError as exc:
            duration_ms = (time.monotonic() - start) * 1000
            await _write_access_log(
                db,
                request=request,
                path=f"/api/v1/data/{full_path}",
                status_code=500,
                duration_ms=duration_ms,
                principal=principal,
                endpoint_id=endpoint_id,
            )
            log.error(
                "data_endpoint_query_failed",
                endpoint_id=str(endpoint_id),
                path=path,
                error=str(exc),
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Query execution failed."},
            )

        # Apply column mapping
        mapped_rows = _apply_column_map(rows, ep.column_map_json or {})

        duration_ms = (time.monotonic() - start) * 1000

        # Write access log
        await _write_access_log(
            db,
            request=request,
            path=f"/api/v1/data/{full_path}",
            status_code=200,
            duration_ms=duration_ms,
            principal=principal,
            endpoint_id=endpoint_id,
        )

        # Build response
        response_headers: dict[str, str] = {}
        if ep.is_deprecated:
            response_headers["Deprecation"] = "true"
            if ep.deprecation_note:
                response_headers["Sunset"] = ep.deprecation_note

        return JSONResponse(
            status_code=200,
            content={
                "data": mapped_rows,
                "meta": {
                    "row_count": len(mapped_rows),
                    "query_duration_ms": query_duration_ms,
                    "endpoint": path,
                    "version": ep.version,
                    "data_strategy": ep.data_strategy.value,
                },
            },
            headers=response_headers,
        )

    except HTTPException:
        raise
    except Exception as exc:
        duration_ms = (time.monotonic() - start) * 1000
        await _write_access_log(
            db,
            request=request,
            path=f"/api/v1/data/{full_path}",
            status_code=500,
            duration_ms=duration_ms,
            principal=principal,
            endpoint_id=endpoint_id,
        )
        log.error(
            "data_endpoint_unhandled_error",
            path=full_path,
            error=str(exc),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error."},
        )
