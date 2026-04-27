"""Verify Oracle client initialization moved from per-request to startup.

The previous implementation called ``oracledb.init_oracle_client`` inside
``_execute_sync`` on every thick-mode query. The function is intended to
be invoked once per process; calling it repeatedly is wasteful and on
some platforms erratic. Phase 4 lifted it to the FastAPI lifespan.
"""

import sys
from types import ModuleType
from unittest.mock import MagicMock

import pytest


@pytest.fixture()
def fake_oracledb(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Install a stub ``oracledb`` module so the test doesn't require the
    real Oracle Instant Client (which isn't present in CI)."""
    stub = ModuleType("oracledb")
    init_mock = MagicMock()
    stub.init_oracle_client = init_mock  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "oracledb", stub)
    return init_mock


def test_init_oracle_client_called_once_when_lib_dir_set(
    monkeypatch: pytest.MonkeyPatch,
    fake_oracledb: MagicMock,
) -> None:
    """The lifespan helper invokes init exactly once with the configured path."""
    monkeypatch.setattr(
        "app.main.settings.oracle_client_lib_dir",
        "/opt/oracle/instantclient_23",
    )
    from app.main import _init_oracle_client

    _init_oracle_client()

    fake_oracledb.assert_called_once_with(lib_dir="/opt/oracle/instantclient_23")


def test_init_oracle_client_skipped_when_lib_dir_blank(
    monkeypatch: pytest.MonkeyPatch,
    fake_oracledb: MagicMock,
) -> None:
    """Thin-mode deployments must not import oracledb at startup."""
    monkeypatch.setattr("app.main.settings.oracle_client_lib_dir", "")
    from app.main import _init_oracle_client

    _init_oracle_client()

    fake_oracledb.assert_not_called()


def test_init_oracle_client_swallows_failures(
    monkeypatch: pytest.MonkeyPatch,
    fake_oracledb: MagicMock,
) -> None:
    """A bootstrap failure must not crash the app — the surfaced error
    should come from the first connection attempt instead."""
    monkeypatch.setattr(
        "app.main.settings.oracle_client_lib_dir",
        "/opt/oracle/instantclient_23",
    )
    fake_oracledb.side_effect = RuntimeError("DPI-1047: cannot locate libclntsh")
    from app.main import _init_oracle_client

    # No exception expected — the warning is logged instead.
    _init_oracle_client()
