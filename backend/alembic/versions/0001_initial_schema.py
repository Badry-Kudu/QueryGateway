"""Initial schema — all Phase 1 domain tables.

Revision ID: 0001
Revises:
Create Date: 2026-03-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── Enum types ────────────────────────────────────────────────────────────
    oracle_mode = postgresql.ENUM("thin", "thick", name="oracle_mode", create_type=False)
    oracle_mode.create(op.get_bind(), checkfirst=True)

    auth_method_type = postgresql.ENUM(
        "bearer", "basic", "api_key", name="auth_method_type", create_type=False
    )
    auth_method_type.create(op.get_bind(), checkfirst=True)

    data_strategy = postgresql.ENUM(
        "live", "snapshot", name="data_strategy", create_type=False
    )
    data_strategy.create(op.get_bind(), checkfirst=True)

    schedule_type = postgresql.ENUM(
        "cron", "interval", name="schedule_type", create_type=False
    )
    schedule_type.create(op.get_bind(), checkfirst=True)

    job_run_status = postgresql.ENUM(
        "running", "success", "failed", "timeout", name="job_run_status", create_type=False
    )
    job_run_status.create(op.get_bind(), checkfirst=True)

    # ── connections ───────────────────────────────────────────────────────────
    op.create_table(
        "connections",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.String(1000), nullable=True),
        sa.Column("host", sa.String(255), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False, server_default="1521"),
        sa.Column("service_name", sa.String(255), nullable=True),
        sa.Column("sid", sa.String(255), nullable=True),
        sa.Column("username", sa.String(255), nullable=False),
        sa.Column("encrypted_password", sa.LargeBinary(), nullable=False),
        sa.Column("pool_min", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("pool_max", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("pool_timeout", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("query_timeout", sa.Integer(), nullable=False, server_default="30"),
        sa.Column(
            "mode",
            postgresql.ENUM("thin", "thick", name="oracle_mode", create_type=False),
            nullable=False,
            server_default="thin",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # ── auth_methods ──────────────────────────────────────────────────────────
    op.create_table(
        "auth_methods",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.String(1000), nullable=True),
        sa.Column(
            "method_type",
            postgresql.ENUM(
                "bearer", "basic", "api_key", name="auth_method_type", create_type=False
            ),
            nullable=False,
        ),
        sa.Column(
            "config_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # ── endpoints ─────────────────────────────────────────────────────────────
    op.create_table(
        "endpoints",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.String(1000), nullable=True),
        sa.Column("path", sa.String(500), nullable=False),
        sa.Column("connection_id", sa.UUID(), nullable=False),
        sa.Column("sql_text", sa.Text(), nullable=False),
        sa.Column(
            "param_schema_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "column_map_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("auth_method_id", sa.UUID(), nullable=True),
        sa.Column(
            "data_strategy",
            postgresql.ENUM("live", "snapshot", name="data_strategy", create_type=False),
            nullable=False,
            server_default="live",
        ),
        sa.Column("version", sa.String(10), nullable=False, server_default="v1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_deprecated", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deprecation_note", sa.String(1000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["connection_id"], ["connections.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["auth_method_id"], ["auth_methods.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("path"),
    )

    # ── schedules ─────────────────────────────────────────────────────────────
    op.create_table(
        "schedules",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("endpoint_id", sa.UUID(), nullable=False),
        sa.Column(
            "schedule_type",
            postgresql.ENUM("cron", "interval", name="schedule_type", create_type=False),
            nullable=False,
        ),
        sa.Column("cron_expression", sa.String(100), nullable=True),
        sa.Column("interval_seconds", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["endpoint_id"], ["endpoints.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── job_runs ──────────────────────────────────────────────────────────────
    op.create_table(
        "job_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("schedule_id", sa.UUID(), nullable=False),
        sa.Column("endpoint_id", sa.UUID(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "running", "success", "failed", "timeout",
                name="job_run_status",
                create_type=False,
            ),
            nullable=False,
            server_default="running",
        ),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("error_detail", sa.String(5000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["endpoint_id"], ["endpoints.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["schedule_id"], ["schedules.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── snapshots ─────────────────────────────────────────────────────────────
    op.create_table(
        "snapshots",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("endpoint_id", sa.UUID(), nullable=False),
        sa.Column("job_run_id", sa.UUID(), nullable=True),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["endpoint_id"], ["endpoints.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_run_id"], ["job_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── access_logs ───────────────────────────────────────────────────────────
    op.create_table(
        "access_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("endpoint_id", sa.UUID(), nullable=True),
        sa.Column("path", sa.String(500), nullable=False),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("principal", sa.String(255), nullable=True),
        sa.Column("remote_ip", sa.String(45), nullable=True),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Float(), nullable=False),
        sa.Column("request_id", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_access_logs_request_id", "access_logs", ["request_id"])
    op.create_index("ix_access_logs_created_at", "access_logs", ["created_at"])

    # ── app_settings ──────────────────────────────────────────────────────────
    op.create_table(
        "app_settings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("key", sa.String(255), nullable=False),
        sa.Column("value", sa.String(5000), nullable=False),
        sa.Column("description", sa.String(1000), nullable=True),
        sa.Column("is_secret", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_by", sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )


def downgrade() -> None:
    op.drop_table("app_settings")
    op.drop_index("ix_access_logs_created_at", "access_logs")
    op.drop_index("ix_access_logs_request_id", "access_logs")
    op.drop_table("access_logs")
    op.drop_table("snapshots")
    op.drop_table("job_runs")
    op.drop_table("schedules")
    op.drop_table("endpoints")
    op.drop_table("auth_methods")
    op.drop_table("connections")

    op.execute("DROP TYPE IF EXISTS job_run_status")
    op.execute("DROP TYPE IF EXISTS schedule_type")
    op.execute("DROP TYPE IF EXISTS data_strategy")
    op.execute("DROP TYPE IF EXISTS auth_method_type")
    op.execute("DROP TYPE IF EXISTS oracle_mode")
