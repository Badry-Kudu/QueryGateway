"""Connection service — business logic for Oracle connection management.

Responsibilities:
- Validate uniqueness and business constraints before persistence.
- Encrypt / decrypt credentials via the crypto module.
- Orchestrate Oracle connectivity tests via python-oracledb thin mode.
- Emit structured audit log entries for create / update / delete / test.
"""

import time
import uuid
from collections.abc import Sequence

import structlog

from app.crypto import decrypt_password, encrypt_password
from app.models.connection import OracleConnection
from app.repositories.connection import ConnectionRepository
from app.schemas.connection import (
    ConnectionCreate,
    ConnectionResponse,
    ConnectionTestResult,
    ConnectionUpdate,
)

log = structlog.get_logger()


def _to_response(obj: OracleConnection) -> ConnectionResponse:
    return ConnectionResponse(
        id=obj.id,
        name=obj.name,
        description=obj.description,
        host=obj.host,
        port=obj.port,
        service_name=obj.service_name,
        sid=obj.sid,
        username=obj.username,
        has_password=bool(obj.encrypted_password),
        pool_min=obj.pool_min,
        pool_max=obj.pool_max,
        pool_timeout=obj.pool_timeout,
        query_timeout=obj.query_timeout,
        mode=obj.mode,
        is_active=obj.is_active,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


class ConnectionService:
    """Business logic layer for Oracle connection management."""

    def __init__(self, repo: ConnectionRepository) -> None:
        self._repo = repo

    async def list_connections(self, *, active_only: bool = False) -> Sequence[ConnectionResponse]:
        rows = await self._repo.get_all(active_only=active_only)
        return [_to_response(r) for r in rows]

    async def get_connection(self, connection_id: uuid.UUID) -> ConnectionResponse | None:
        obj = await self._repo.get_by_id(connection_id)
        return _to_response(obj) if obj else None

    async def create_connection(
        self, payload: ConnectionCreate, *, actor: str = "system"
    ) -> ConnectionResponse:
        existing = await self._repo.get_by_name(payload.name)
        if existing:
            raise ValueError(f"A connection named '{payload.name}' already exists.")

        obj = OracleConnection(
            name=payload.name,
            description=payload.description,
            host=payload.host,
            port=payload.port,
            service_name=payload.service_name,
            sid=payload.sid,
            username=payload.username,
            encrypted_password=encrypt_password(payload.password),
            pool_min=payload.pool_min,
            pool_max=payload.pool_max,
            pool_timeout=payload.pool_timeout,
            query_timeout=payload.query_timeout,
            mode=payload.mode,
            is_active=payload.is_active,
        )
        obj = await self._repo.create(obj)

        log.info(
            "connection_created",
            connection_id=str(obj.id),
            name=obj.name,
            actor=actor,
        )
        return _to_response(obj)

    async def update_connection(
        self,
        connection_id: uuid.UUID,
        payload: ConnectionUpdate,
        *,
        actor: str = "system",
    ) -> ConnectionResponse | None:
        obj = await self._repo.get_by_id(connection_id)
        if obj is None:
            return None

        changes: dict[str, object] = {}
        for field in (
            "name",
            "description",
            "host",
            "port",
            "service_name",
            "sid",
            "username",
            "pool_min",
            "pool_max",
            "pool_timeout",
            "query_timeout",
            "mode",
            "is_active",
        ):
            value = getattr(payload, field)
            if value is not None:
                changes[field] = value

        if payload.name is not None and payload.name != obj.name:
            conflict = await self._repo.get_by_name(payload.name)
            if conflict:
                raise ValueError(f"A connection named '{payload.name}' already exists.")

        if payload.password is not None:
            changes["encrypted_password"] = encrypt_password(payload.password)

        obj = await self._repo.update(obj, changes)

        log.info(
            "connection_updated",
            connection_id=str(obj.id),
            name=obj.name,
            changed_fields=list(changes.keys()),
            actor=actor,
        )
        return _to_response(obj)

    async def delete_connection(
        self, connection_id: uuid.UUID, *, actor: str = "system"
    ) -> bool:
        obj = await self._repo.get_by_id(connection_id)
        if obj is None:
            return False

        name = obj.name
        await self._repo.delete(obj)

        log.info(
            "connection_deleted",
            connection_id=str(connection_id),
            name=name,
            actor=actor,
        )
        return True

    async def test_connection(
        self, connection_id: uuid.UUID, *, actor: str = "system"
    ) -> ConnectionTestResult:
        obj = await self._repo.get_by_id(connection_id)
        if obj is None:
            return ConnectionTestResult(success=False, message="Connection not found.")

        try:
            password = decrypt_password(obj.encrypted_password)
        except ValueError:
            log.warning(
                "connection_test_decrypt_failed",
                connection_id=str(connection_id),
                actor=actor,
            )
            return ConnectionTestResult(
                success=False,
                message="Failed to decrypt stored credentials — re-save the connection.",
            )

        dsn: str
        if obj.service_name:
            dsn = f"{obj.host}:{obj.port}/{obj.service_name}"
        else:
            dsn = f"{obj.host}:{obj.port}/{obj.sid}"

        start = time.monotonic()
        try:
            import oracledb  # noqa: PLC0415

            conn = oracledb.connect(
                user=obj.username,
                password=password,
                dsn=dsn,
                mode=oracledb.DEFAULT_AUTH,
            )
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT banner FROM v$version WHERE rownum = 1")
                row = cursor.fetchone()
                oracle_version = row[0] if row else None
            finally:
                conn.close()

            duration_ms = (time.monotonic() - start) * 1000
            log.info(
                "connection_test_success",
                connection_id=str(connection_id),
                name=obj.name,
                duration_ms=round(duration_ms, 2),
                actor=actor,
            )
            return ConnectionTestResult(
                success=True,
                message="Connection successful.",
                duration_ms=round(duration_ms, 2),
                oracle_version=oracle_version,
            )

        except Exception as exc:
            duration_ms = (time.monotonic() - start) * 1000
            log.warning(
                "connection_test_failed",
                connection_id=str(connection_id),
                name=obj.name,
                error=str(exc),
                duration_ms=round(duration_ms, 2),
                actor=actor,
            )
            return ConnectionTestResult(
                success=False,
                message=f"Connection failed: {exc}",
                duration_ms=round(duration_ms, 2),
            )
