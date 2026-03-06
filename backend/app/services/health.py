"""Health aggregation service — system-wide health status.

Responsibilities:
- Probe PostgreSQL connectivity.
- Report scheduler status (running/stopped, active job count).
- Summarize recent job outcomes.
- Detect stale snapshots.
- Aggregate into a single dashboard response.
"""

from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.endpoint import ApiEndpoint
from app.models.job_run import JobRun
from app.models.schedule import Schedule
from app.models.snapshot import Snapshot
from app.services.scheduler import get_scheduler

log = structlog.get_logger()


class HealthDashboardResponse:
    """Structured health dashboard data (converted to dict for JSON)."""

    def __init__(self) -> None:
        self.overall: str = "ok"
        self.components: dict[str, dict[str, object]] = {}
        self.scheduler: dict[str, object] = {}
        self.recent_jobs: dict[str, object] = {}
        self.stale_snapshots: list[dict[str, object]] = []

    def to_dict(self) -> dict[str, object]:
        return {
            "overall": self.overall,
            "components": self.components,
            "scheduler": self.scheduler,
            "recent_jobs": self.recent_jobs,
            "stale_snapshots": self.stale_snapshots,
        }


async def get_health_dashboard(db: AsyncSession) -> dict[str, object]:
    """Aggregate system health into a dashboard response."""
    dashboard = HealthDashboardResponse()

    # ── PostgreSQL probe ──────────────────────────────────────────────────
    try:
        await db.execute(text("SELECT 1"))
        dashboard.components["database"] = {"status": "ok"}
    except Exception as exc:
        dashboard.components["database"] = {"status": "error", "detail": str(exc)}
        dashboard.overall = "degraded"

    # ── Scheduler status ──────────────────────────────────────────────────
    sched = get_scheduler()
    if sched is not None:
        try:
            running = sched.running
            jobs = sched.get_jobs()
            dashboard.scheduler = {
                "status": "running" if running else "stopped",
                "job_count": len(jobs),
            }
        except Exception:  # noqa: BLE001
            dashboard.scheduler = {"status": "unknown"}
    else:
        dashboard.scheduler = {"status": "not_initialized"}

    # ── Active schedules count ────────────────────────────────────────────
    try:
        result = await db.execute(
            select(func.count()).select_from(Schedule).where(Schedule.is_active.is_(True))
        )
        active_schedules = result.scalar() or 0
        dashboard.scheduler["active_schedules"] = active_schedules
    except Exception:  # noqa: BLE001
        log.debug("health_active_schedules_query_failed")

    # ── Recent job outcomes (last 24h) ────────────────────────────────────
    try:
        cutoff = datetime.now(UTC) - timedelta(hours=24)

        total_result = await db.execute(
            select(func.count()).select_from(JobRun).where(JobRun.started_at >= cutoff)
        )
        total_24h = total_result.scalar() or 0

        success_result = await db.execute(
            select(func.count())
            .select_from(JobRun)
            .where(JobRun.started_at >= cutoff, JobRun.status == "success")
        )
        success_24h = success_result.scalar() or 0

        failed_result = await db.execute(
            select(func.count())
            .select_from(JobRun)
            .where(
                JobRun.started_at >= cutoff,
                JobRun.status.in_(["failed", "timeout"]),
            )
        )
        failed_24h = failed_result.scalar() or 0

        dashboard.recent_jobs = {
            "total_24h": total_24h,
            "success_24h": success_24h,
            "failed_24h": failed_24h,
            "success_rate": (
                round(success_24h / total_24h * 100, 1) if total_24h > 0 else None
            ),
        }
    except Exception:  # noqa: BLE001
        dashboard.recent_jobs = {"total_24h": 0, "success_24h": 0, "failed_24h": 0}

    # ── Stale snapshot detection ──────────────────────────────────────────
    # Find snapshot-strategy endpoints where latest snapshot is older than 2x
    # their schedule interval (or older than 24h if no schedule found).
    try:
        snapshot_endpoints_result = await db.execute(
            select(ApiEndpoint).where(ApiEndpoint.data_strategy == "snapshot")
        )
        snapshot_endpoints = snapshot_endpoints_result.scalars().all()

        stale: list[dict[str, object]] = []
        for ep in snapshot_endpoints:
            if not ep.is_active:
                continue

            # Get latest snapshot
            snap_result = await db.execute(
                select(Snapshot)
                .where(Snapshot.endpoint_id == ep.id)
                .order_by(Snapshot.created_at.desc())
                .limit(1)
            )
            latest_snap = snap_result.scalar_one_or_none()

            if latest_snap is None:
                stale.append({
                    "endpoint_id": str(ep.id),
                    "endpoint_name": ep.name,
                    "reason": "no_snapshot",
                })
                continue

            # Get schedule for this endpoint
            sched_result = await db.execute(
                select(Schedule).where(Schedule.endpoint_id == ep.id)
            )
            schedule = sched_result.scalar_one_or_none()

            # Determine staleness threshold
            threshold_hours = 24.0
            if schedule and schedule.interval_seconds:
                threshold_hours = max(
                    schedule.interval_seconds * 2 / 3600, 1.0
                )

            age = datetime.now(UTC) - latest_snap.created_at.astimezone(UTC)
            if age > timedelta(hours=threshold_hours):
                stale.append({
                    "endpoint_id": str(ep.id),
                    "endpoint_name": ep.name,
                    "reason": "stale",
                    "last_snapshot_age_hours": round(age.total_seconds() / 3600, 1),
                    "threshold_hours": threshold_hours,
                })

        dashboard.stale_snapshots = stale
        if stale:
            dashboard.overall = "degraded"

    except Exception:  # noqa: BLE001
        log.debug("health_stale_snapshot_check_failed")

    # ── Endpoint / connection counts ──────────────────────────────────────
    try:
        from app.models.connection import OracleConnection  # noqa: PLC0415

        conn_result = await db.execute(
            select(func.count()).select_from(OracleConnection)
        )
        active_conn_result = await db.execute(
            select(func.count())
            .select_from(OracleConnection)
            .where(OracleConnection.is_active.is_(True))
        )
        ep_result = await db.execute(
            select(func.count()).select_from(ApiEndpoint)
        )
        active_ep_result = await db.execute(
            select(func.count())
            .select_from(ApiEndpoint)
            .where(ApiEndpoint.is_active.is_(True))
        )

        dashboard.components["connections"] = {
            "total": conn_result.scalar() or 0,
            "active": active_conn_result.scalar() or 0,
        }
        dashboard.components["endpoints"] = {
            "total": ep_result.scalar() or 0,
            "active": active_ep_result.scalar() or 0,
        }
    except Exception:  # noqa: BLE001
        log.debug("health_counts_query_failed")

    return dashboard.to_dict()
