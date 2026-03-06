"""Health check endpoints.

GET /api/v1/admin/health/live      — Liveness probe (no dependencies checked).
GET /api/v1/admin/health/ready     — Readiness probe (checks PostgreSQL connectivity).
GET /api/v1/admin/health/dashboard — Aggregated system health dashboard.

Container orchestrators should call /live for restart decisions and /ready
to gate traffic routing.
"""

import structlog
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.health import HealthCheck
from app.services.health import get_health_dashboard

log = structlog.get_logger()

router = APIRouter(prefix="/api/v1/admin/health", tags=["health"])


@router.get(
    "/live",
    response_model=HealthCheck,
    summary="Liveness probe",
    description="Returns 200 as long as the process is running.",
)
async def liveness() -> HealthCheck:
    return HealthCheck(status="ok")


@router.get(
    "/ready",
    response_model=HealthCheck,
    summary="Readiness probe",
    description="Returns 200 when the app can serve traffic (DB reachable).",
    responses={503: {"description": "Service unavailable — dependency degraded"}},
)
async def readiness(db: AsyncSession = Depends(get_db)) -> JSONResponse:
    checks: dict[str, str] = {}

    try:
        await db.execute(text("SELECT 1"))
        checks["db"] = "ok"
    except Exception as exc:
        log.error("db_health_check_failed", error=str(exc))
        checks["db"] = "error"
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=HealthCheck(status="degraded", checks=checks).model_dump(),
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=HealthCheck(status="ok", checks=checks).model_dump(),
    )


@router.get(
    "/dashboard",
    summary="Health dashboard",
    description=(
        "Aggregated system health: DB connectivity, scheduler status, "
        "recent job outcomes, stale snapshot detection, resource counts."
    ),
)
async def dashboard(db: AsyncSession = Depends(get_db)) -> JSONResponse:
    data = await get_health_dashboard(db)
    overall = data.get("overall", "ok")
    status_code = (
        status.HTTP_200_OK
        if overall == "ok"
        else status.HTTP_200_OK  # Still 200 — "degraded" is informational
    )
    return JSONResponse(status_code=status_code, content=data)
