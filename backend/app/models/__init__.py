"""ORM model registry.

Import all models here so Alembic's env.py picks them up for autogenerate
via ``Base.metadata`` without needing to import each file individually.
"""

from app.models.access_log import AccessLog
from app.models.auth_method import AuthMethod, AuthMethodType
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.connection import OracleConnection, OracleMode
from app.models.endpoint import ApiEndpoint, DataStrategy
from app.models.job_run import JobRun, JobRunStatus
from app.models.schedule import Schedule, ScheduleType
from app.models.setting import AppSetting
from app.models.snapshot import Snapshot

__all__ = [
    "Base",
    "TimestampMixin",
    "UUIDPrimaryKeyMixin",
    "OracleConnection",
    "OracleMode",
    "AuthMethod",
    "AuthMethodType",
    "ApiEndpoint",
    "DataStrategy",
    "Schedule",
    "ScheduleType",
    "JobRun",
    "JobRunStatus",
    "Snapshot",
    "AccessLog",
    "AppSetting",
]
