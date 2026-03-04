"""Connection management endpoints.

Admin API — all routes under /api/v1/admin/connections.

Routes:
    GET    /                — List all connections
    POST   /                — Create a connection
    GET    /{id}            — Get a single connection
    PUT    /{id}            — Update a connection
    DELETE /{id}            — Delete a connection
    POST   /{id}/test       — Test Oracle connectivity
"""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.repositories.connection import ConnectionRepository
from app.schemas.connection import (
    ConnectionCreate,
    ConnectionResponse,
    ConnectionTestResult,
    ConnectionUpdate,
)
from app.services.connection import ConnectionService

log = structlog.get_logger()

router = APIRouter(prefix="/api/v1/admin/connections", tags=["connections"])


def _service(db: AsyncSession = Depends(get_db)) -> ConnectionService:
    return ConnectionService(ConnectionRepository(db))


@router.get(
    "/",
    response_model=list[ConnectionResponse],
    summary="List connections",
)
async def list_connections(
    active_only: bool = Query(False, description="Return only active connections."),
    svc: ConnectionService = Depends(_service),
) -> list[ConnectionResponse]:
    return list(await svc.list_connections(active_only=active_only))


@router.post(
    "/",
    response_model=ConnectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create connection",
)
async def create_connection(
    payload: ConnectionCreate,
    db: AsyncSession = Depends(get_db),
) -> ConnectionResponse:
    svc = ConnectionService(ConnectionRepository(db))
    try:
        result = await svc.create_connection(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    await db.commit()
    return result


@router.get(
    "/{connection_id}",
    response_model=ConnectionResponse,
    summary="Get connection",
)
async def get_connection(
    connection_id: uuid.UUID,
    svc: ConnectionService = Depends(_service),
) -> ConnectionResponse:
    result = await svc.get_connection(connection_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found.")
    return result


@router.put(
    "/{connection_id}",
    response_model=ConnectionResponse,
    summary="Update connection",
)
async def update_connection(
    connection_id: uuid.UUID,
    payload: ConnectionUpdate,
    db: AsyncSession = Depends(get_db),
) -> ConnectionResponse:
    svc = ConnectionService(ConnectionRepository(db))
    try:
        result = await svc.update_connection(connection_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found.")
    await db.commit()
    return result


@router.delete(
    "/{connection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete connection",
)
async def delete_connection(
    connection_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    svc = ConnectionService(ConnectionRepository(db))
    deleted = await svc.delete_connection(connection_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found.")
    await db.commit()


@router.post(
    "/{connection_id}/test",
    response_model=ConnectionTestResult,
    summary="Test Oracle connectivity",
    description=(
        "Attempts a live connection to the Oracle instance.  "
        "Returns diagnostic details regardless of success or failure.  "
        "Does NOT modify any stored data."
    ),
)
async def test_connection(
    connection_id: uuid.UUID,
    svc: ConnectionService = Depends(_service),
) -> ConnectionTestResult:
    result = await svc.test_connection(connection_id)
    if not result.success and result.message == "Connection not found.":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result.message)
    return result
