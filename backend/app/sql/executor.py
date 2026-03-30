"""SQL execution engine for Oracle queries.

Responsibilities:
- Execute parameterized SQL against Oracle connections via python-oracledb.
- Enforce bind-variable-only execution (no string interpolation).
- Apply query timeout from connection configuration.
- Return structured column/row results for preview and live data serving.

All Oracle access is synchronous (oracledb blocking driver) and delegated to
a thread via ``anyio.to_thread.run_sync`` to keep the event loop free.
"""

import time
from functools import partial

import anyio
import structlog

from app.crypto import decrypt_password
from app.models.connection import OracleConnection

log = structlog.get_logger()


class SqlExecutionError(Exception):
    """Raised when SQL execution fails."""


def _build_dsn(conn: OracleConnection) -> str:
    if conn.service_name:
        return f"{conn.host}:{conn.port}/{conn.service_name}"
    return f"{conn.host}:{conn.port}/{conn.sid}"


def _execute_sync(
    username: str,
    password: str,
    dsn: str,
    sql: str,
    params: dict[str, object],
    max_rows: int,
    query_timeout: int,
    thick: bool = False,
    lib_dir: str = "",
) -> tuple[list[str], list[dict[str, object]]]:
    """Blocking Oracle execution — runs in a thread."""
    import oracledb  # noqa: PLC0415

    if thick:
        oracledb.init_oracle_client(lib_dir=lib_dir or None)
    conn = oracledb.connect(user=username, password=password, dsn=dsn)
    try:
        conn.call_timeout = query_timeout * 1000  # milliseconds
        cursor = conn.cursor()
        cursor.execute(sql, params)

        columns = [col[0] for col in cursor.description] if cursor.description else []
        rows_raw = cursor.fetchmany(max_rows)

        rows: list[dict[str, object]] = []
        for row in rows_raw:
            row_dict: dict[str, object] = {}
            for i, col in enumerate(columns):
                val = row[i]
                # Convert non-JSON-serializable types to strings
                if val is not None and not isinstance(val, str | int | float | bool):
                    val = str(val)
                row_dict[col] = val
            rows.append(row_dict)

        return columns, rows
    finally:
        conn.close()


async def execute_query(
    connection: OracleConnection,
    sql: str,
    params: dict[str, object],
    max_rows: int = 1000,
) -> tuple[list[str], list[dict[str, object]], float]:
    """Execute a parameterized SQL query against an Oracle connection.

    Returns (columns, rows, duration_ms).
    Raises SqlExecutionError on failure.
    """
    try:
        password = decrypt_password(connection.encrypted_password)
    except ValueError as exc:
        raise SqlExecutionError(
            "Failed to decrypt stored credentials — re-save the connection."
        ) from exc

    dsn = _build_dsn(connection)
    start = time.monotonic()

    try:
        from app.config import settings  # noqa: PLC0415
        columns, rows = await anyio.to_thread.run_sync(
            partial(
                _execute_sync,
                connection.username,
                password,
                dsn,
                sql,
                params,
                max_rows,
                connection.query_timeout,
                connection.mode == "thick",
                settings.oracle_client_lib_dir,
            )
        )
        duration_ms = (time.monotonic() - start) * 1000

        log.info(
            "sql_execution_success",
            connection_id=str(connection.id),
            row_count=len(rows),
            duration_ms=round(duration_ms, 2),
        )

        return columns, rows, round(duration_ms, 2)

    except Exception as exc:
        duration_ms = (time.monotonic() - start) * 1000
        log.warning(
            "sql_execution_failed",
            connection_id=str(connection.id),
            error=str(exc),
            duration_ms=round(duration_ms, 2),
        )
        raise SqlExecutionError(f"Query execution failed: {exc}") from exc
