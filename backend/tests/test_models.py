"""Model instantiation and schema sanity tests.

These tests confirm that:
- All ORM models can be instantiated with valid data (no DB required).
- Enum values match the project spec.
- Table names are correctly declared.
"""

import uuid
from datetime import UTC

from app.models.access_log import AccessLog
from app.models.auth_method import AuthMethod, AuthMethodType
from app.models.connection import OracleConnection, OracleMode
from app.models.endpoint import ApiEndpoint, DataStrategy
from app.models.job_run import JobRun, JobRunStatus
from app.models.schedule import Schedule, ScheduleType
from app.models.setting import AppSetting
from app.models.snapshot import Snapshot

# ── Table name assertions ─────────────────────────────────────────────────────


def test_table_names() -> None:
    assert OracleConnection.__tablename__ == "connections"
    assert AuthMethod.__tablename__ == "auth_methods"
    assert ApiEndpoint.__tablename__ == "endpoints"
    assert Schedule.__tablename__ == "schedules"
    assert JobRun.__tablename__ == "job_runs"
    assert Snapshot.__tablename__ == "snapshots"
    assert AccessLog.__tablename__ == "access_logs"
    assert AppSetting.__tablename__ == "app_settings"


# ── Enum value coverage ───────────────────────────────────────────────────────


def test_oracle_mode_values() -> None:
    assert set(OracleMode) == {OracleMode.thin, OracleMode.thick}


def test_auth_method_type_values() -> None:
    assert set(AuthMethodType) == {
        AuthMethodType.bearer,
        AuthMethodType.basic,
        AuthMethodType.api_key,
    }


def test_data_strategy_values() -> None:
    assert set(DataStrategy) == {DataStrategy.live, DataStrategy.snapshot}


def test_schedule_type_values() -> None:
    assert set(ScheduleType) == {ScheduleType.cron, ScheduleType.interval}


def test_job_run_status_values() -> None:
    assert set(JobRunStatus) == {
        JobRunStatus.running,
        JobRunStatus.success,
        JobRunStatus.failed,
        JobRunStatus.timeout,
    }


# ── Model instantiation ───────────────────────────────────────────────────────


def test_oracle_connection_instantiation() -> None:
    conn = OracleConnection(
        name="test-conn",
        host="oracle.example.com",
        port=1521,
        service_name="XEPDB1",
        username="dbuser",
        encrypted_password=b"placeholder",
        mode=OracleMode.thin,
        pool_min=1,
        pool_max=5,
    )
    assert conn.name == "test-conn"
    assert conn.mode == OracleMode.thin
    # pool_min/pool_max are explicit here; mapped_column(default=) is an INSERT
    # default only, not an __init__ default.
    assert conn.pool_min == 1
    assert conn.pool_max == 5


def test_auth_method_instantiation() -> None:
    am = AuthMethod(
        name="my-bearer",
        method_type=AuthMethodType.bearer,
        config_json={"expiry_seconds": 3600},
    )
    assert am.method_type == AuthMethodType.bearer
    assert am.config_json["expiry_seconds"] == 3600


def test_api_endpoint_instantiation() -> None:
    conn_id = uuid.uuid4()
    ep = ApiEndpoint(
        name="users-endpoint",
        path="users",
        connection_id=conn_id,
        sql_text="SELECT * FROM users WHERE id = :user_id",
        data_strategy=DataStrategy.live,
    )
    assert ep.path == "users"
    assert ep.data_strategy == DataStrategy.live
    # is_deprecated has a Python-level default=False via SQLAlchemy column default.
    # Test the explicitly-set value via the attribute assigned at construction.
    assert ep.is_deprecated in (False, None)  # DB default; None until persisted


def test_schedule_instantiation() -> None:
    ep_id = uuid.uuid4()
    sched = Schedule(
        endpoint_id=ep_id,
        schedule_type=ScheduleType.cron,
        cron_expression="0 * * * *",
    )
    assert sched.schedule_type == ScheduleType.cron
    assert sched.cron_expression == "0 * * * *"


def test_job_run_instantiation() -> None:
    from datetime import datetime

    jr = JobRun(
        schedule_id=uuid.uuid4(),
        endpoint_id=uuid.uuid4(),
        started_at=datetime.now(tz=UTC),
        status=JobRunStatus.running,
    )
    assert jr.status == JobRunStatus.running
    assert jr.finished_at is None


def test_app_setting_instantiation() -> None:
    setting = AppSetting(key="log_level", value="DEBUG", description="Logging verbosity")
    assert setting.key == "log_level"
    # is_secret default is applied at DB INSERT time, not Python construction.
    assert setting.is_secret in (False, None)
