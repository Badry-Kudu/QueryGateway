"""Auth method management endpoints.

Admin API — all routes under /api/v1/admin/auth.

Routes:
    GET    /                    — List auth methods
    POST   /                    — Create auth method
    GET    /{id}                — Get single auth method
    PUT    /{id}                — Update auth method
    DELETE /{id}                — Delete auth method
    POST   /{id}/issue-token    — Issue JWT (bearer only)
    POST   /{id}/rotate         — Rotate signing secret or API key
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.admin import get_current_admin
from app.dependencies import get_db
from app.repositories.auth_method import AuthMethodRepository
from app.schemas.auth_method import (
    ApiKeyIssuedResponse,
    AuthMethodCreate,
    AuthMethodResponse,
    AuthMethodUpdate,
    RotateResponse,
    TokenIssuedResponse,
)
from app.services.auth_method import AuthMethodService

router = APIRouter(
    prefix="/api/v1/admin/auth",
    tags=["auth-methods"],
    dependencies=[Depends(get_current_admin)],
)


def _service(db: AsyncSession = Depends(get_db)) -> AuthMethodService:
    return AuthMethodService(AuthMethodRepository(db))


@router.get(
    "/",
    response_model=list[AuthMethodResponse],
    summary="List auth methods",
)
async def list_auth_methods(
    active_only: bool = Query(False, description="Return only active auth methods."),
    svc: AuthMethodService = Depends(_service),
) -> list[AuthMethodResponse]:
    return list(await svc.list_auth_methods(active_only=active_only))


@router.post(
    "/",
    response_model=AuthMethodResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create auth method",
    responses={
        201: {"description": "Created. For api_key type use POST /with-key for the one-time key."},
    },
)
async def create_auth_method(
    payload: AuthMethodCreate,
    db: AsyncSession = Depends(get_db),
    svc: AuthMethodService = Depends(_service),
) -> AuthMethodResponse:
    try:
        response, _key = await svc.create_auth_method(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    await db.commit()
    return response


@router.post(
    "/with-key",
    response_model=ApiKeyIssuedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create API key auth method (returns key once)",
    description=(
        "Creates an api_key auth method and returns the plaintext API key. "
        "The key is shown only once and cannot be recovered. "
        "Use the regular POST / endpoint for bearer and basic types."
    ),
)
async def create_api_key_method(
    payload: AuthMethodCreate,
    db: AsyncSession = Depends(get_db),
    svc: AuthMethodService = Depends(_service),
) -> ApiKeyIssuedResponse:
    from app.models.auth_method import AuthMethodType  # noqa: PLC0415

    if payload.method_type != AuthMethodType.api_key:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="This endpoint is for api_key method type only.",
        )
    try:
        _, key_response = await svc.create_auth_method(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    await db.commit()
    if key_response is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Key generation failed.",
        )
    return key_response


@router.get(
    "/{auth_id}",
    response_model=AuthMethodResponse,
    summary="Get auth method",
)
async def get_auth_method(
    auth_id: uuid.UUID,
    svc: AuthMethodService = Depends(_service),
) -> AuthMethodResponse:
    result = await svc.get_auth_method(auth_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Auth method not found.")
    return result


@router.put(
    "/{auth_id}",
    response_model=AuthMethodResponse,
    summary="Update auth method",
)
async def update_auth_method(
    auth_id: uuid.UUID,
    payload: AuthMethodUpdate,
    db: AsyncSession = Depends(get_db),
    svc: AuthMethodService = Depends(_service),
) -> AuthMethodResponse:
    try:
        result = await svc.update_auth_method(auth_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Auth method not found.")
    await db.commit()
    return result


@router.delete(
    "/{auth_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete auth method",
)
async def delete_auth_method(
    auth_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    svc: AuthMethodService = Depends(_service),
) -> None:
    deleted = await svc.delete_auth_method(auth_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Auth method not found.")
    await db.commit()


@router.post(
    "/{auth_id}/issue-token",
    response_model=TokenIssuedResponse,
    summary="Issue JWT (bearer only)",
    description="Creates a signed JWT for a bearer auth method. Not stored server-side.",
)
async def issue_token(
    auth_id: uuid.UUID,
    svc: AuthMethodService = Depends(_service),
) -> TokenIssuedResponse:
    try:
        result = await svc.issue_token(auth_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Auth method not found.")
    return result


@router.post(
    "/{auth_id}/rotate",
    summary="Rotate credentials",
    description=(
        "Bearer: generates new signing secret (old tokens invalid). "
        "API key: generates new key (returned once). "
        "Basic: use PUT to update password."
    ),
)
async def rotate_credentials(
    auth_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    svc: AuthMethodService = Depends(_service),
) -> RotateResponse | ApiKeyIssuedResponse:
    try:
        rotate_resp, key_resp = await svc.rotate_credentials(auth_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    await db.commit()
    return key_resp if key_resp is not None else rotate_resp
