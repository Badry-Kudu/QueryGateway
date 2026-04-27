"""Dynamic data endpoint namespace — /api/v1/data/*.

Phase 4 thinned this file by extracting orchestration into
``app.services.data.DataService`` and access logging into
``app.services.access_log.log_access``. The router is now responsible
only for wiring the request, the service, and the access log.
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.services.access_log import log_access
from app.services.data import DataService

log = structlog.get_logger()

router = APIRouter(prefix="/api/v1/data", tags=["data"])


@router.get(
    "/{full_path:path}",
    summary="Dynamic data endpoint",
    description=(
        "Resolve the endpoint by path, enforce auth, execute SQL or serve "
        "cached snapshot, and return data."
    ),
    include_in_schema=True,
)
async def data_endpoint(
    full_path: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    path = full_path.strip("/").lower()
    full_url = f"/api/v1/data/{full_path}"

    async with log_access(request, path=full_url) as access:
        try:
            result = await DataService(db).serve(path, request)
        except HTTPException as exc:
            # Re-raised so FastAPI returns the correct JSON; the
            # context manager has already recorded the status.
            raise exc

        access.set_principal(result.principal)
        access.set_endpoint_id(result.endpoint_id)
        access.set_status(result.response.status_code)
        return result.response
