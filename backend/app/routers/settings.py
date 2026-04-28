"""Settings management admin API.

Routes under /api/v1/admin/settings:
    GET    /                — List all settings
    GET    /{key}           — Get a single setting
    PUT    /{key}           — Update a single setting
    PUT    /                — Bulk update settings
    GET    /restart-keys    — List settings that require restart
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.admin import get_current_admin
from app.dependencies import get_db
from app.repositories.settings import SettingsRepository
from app.schemas.setting import SettingBulkUpdate, SettingResponse, SettingUpdate
from app.services.settings import SettingsService

log = structlog.get_logger()

router = APIRouter(
    prefix="/api/v1/admin/settings",
    tags=["settings"],
    dependencies=[Depends(get_current_admin)],
)


def _service(db: AsyncSession = Depends(get_db)) -> SettingsService:
    return SettingsService(SettingsRepository(db))


@router.get(
    "/",
    response_model=list[SettingResponse],
    summary="List all settings",
)
async def list_settings(
    db: AsyncSession = Depends(get_db),
    svc: SettingsService = Depends(_service),
) -> list[SettingResponse]:
    result = list(await svc.list_settings())
    await db.commit()
    return result


@router.get(
    "/restart-keys",
    response_model=list[str],
    summary="List restart-required setting keys",
)
async def restart_required_keys(
    svc: SettingsService = Depends(_service),
) -> list[str]:
    return svc.get_restart_required_keys()


@router.get(
    "/{key}",
    response_model=SettingResponse,
    summary="Get setting by key",
)
async def get_setting(
    key: str,
    svc: SettingsService = Depends(_service),
) -> SettingResponse:
    result = await svc.get_setting(key)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Setting '{key}' not found.",
        )
    return result


@router.put(
    "/{key}",
    response_model=SettingResponse,
    summary="Update a single setting",
)
async def update_setting(
    key: str,
    payload: SettingUpdate,
    db: AsyncSession = Depends(get_db),
    svc: SettingsService = Depends(_service),
) -> SettingResponse:
    try:
        result = await svc.update_setting(key, payload.value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    await db.commit()
    return result


@router.put(
    "/",
    response_model=list[SettingResponse],
    summary="Bulk update settings",
)
async def bulk_update_settings(
    payload: SettingBulkUpdate,
    db: AsyncSession = Depends(get_db),
    svc: SettingsService = Depends(_service),
) -> list[SettingResponse]:
    try:
        results = await svc.update_bulk(payload.settings)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    await db.commit()
    return results
