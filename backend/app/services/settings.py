"""Settings service — business logic for application settings.

Responsibilities:
- List / get / update settings with validation.
- Define known settings with defaults and descriptions.
- Mark restart-required vs hot-reloadable settings.
- Seed defaults on first access.
- Mask secret values in responses.
"""

from collections.abc import Sequence

import structlog

from app.repositories.settings import SettingsRepository
from app.schemas.setting import SettingResponse

log = structlog.get_logger()

# Known settings with defaults, descriptions, and metadata.
KNOWN_SETTINGS: dict[str, dict[str, str | bool]] = {
    "log_level": {
        "default": "INFO",
        "description": "Application log level (DEBUG, INFO, WARNING, ERROR).",
        "is_secret": False,
        "restart_required": True,
    },
    "query_timeout_seconds": {
        "default": "30",
        "description": "Maximum query execution time in seconds.",
        "is_secret": False,
        "restart_required": False,
    },
    "cors_origins": {
        "default": "http://localhost:5173,http://localhost:80",
        "description": "Comma-separated list of allowed CORS origins.",
        "is_secret": False,
        "restart_required": True,
    },
    "snapshot_retention_count": {
        "default": "5",
        "description": "Number of snapshots to keep per endpoint.",
        "is_secret": False,
        "restart_required": False,
    },
    "max_job_concurrency": {
        "default": "1",
        "description": "Maximum concurrent scheduled jobs.",
        "is_secret": False,
        "restart_required": True,
    },
}

# Valid log levels for validation
VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


def _mask_value(value: str, is_secret: bool) -> str:
    """Mask secret values for API responses."""
    if is_secret and len(value) > 4:
        return value[:2] + "*" * (len(value) - 4) + value[-2:]
    return value


class SettingsService:
    """Business logic layer for application settings."""

    def __init__(self, repo: SettingsRepository) -> None:
        self._repo = repo

    async def list_settings(self) -> Sequence[SettingResponse]:
        """List all settings, seeding defaults for any missing known settings."""
        existing = await self._repo.get_all()
        existing_keys = {s.key for s in existing}

        # Seed missing known settings
        for key, meta in KNOWN_SETTINGS.items():
            if key not in existing_keys:
                await self._repo.upsert(
                    key=key,
                    value=str(meta["default"]),
                    description=str(meta.get("description", "")),
                    is_secret=bool(meta.get("is_secret", False)),
                    updated_by="system",
                )

        # Re-fetch after seeding
        all_settings = await self._repo.get_all()
        return [
            SettingResponse(
                key=s.key,
                value=_mask_value(s.value, s.is_secret),
                description=s.description,
                is_secret=s.is_secret,
                updated_at=s.updated_at,
                updated_by=s.updated_by,
            )
            for s in all_settings
        ]

    async def get_setting(self, key: str) -> SettingResponse | None:
        obj = await self._repo.get_by_key(key)
        if obj is None:
            return None
        return SettingResponse(
            key=obj.key,
            value=_mask_value(obj.value, obj.is_secret),
            description=obj.description,
            is_secret=obj.is_secret,
            updated_at=obj.updated_at,
            updated_by=obj.updated_by,
        )

    async def update_setting(
        self, key: str, value: str, *, actor: str = "system"
    ) -> SettingResponse:
        """Update a setting value with validation."""
        # Validate known settings
        if key == "log_level" and value.upper() not in VALID_LOG_LEVELS:
            raise ValueError(
                f"Invalid log level '{value}'. "
                f"Must be one of: {', '.join(sorted(VALID_LOG_LEVELS))}."
            )

        if key == "query_timeout_seconds":
            try:
                timeout = int(value)
                if timeout < 1 or timeout > 300:
                    raise ValueError(
                        "Query timeout must be between 1 and 300 seconds."
                    )
            except (ValueError, TypeError) as exc:
                if "must be between" in str(exc):
                    raise
                raise ValueError(
                    "Query timeout must be a valid integer."
                ) from exc

        if key == "snapshot_retention_count":
            try:
                count = int(value)
                if count < 1 or count > 100:
                    raise ValueError(
                        "Snapshot retention count must be between 1 and 100."
                    )
            except (ValueError, TypeError) as exc:
                if "must be between" in str(exc):
                    raise
                raise ValueError(
                    "Snapshot retention count must be a valid integer."
                ) from exc

        if key == "max_job_concurrency":
            try:
                conc = int(value)
                if conc < 1 or conc > 10:
                    raise ValueError(
                        "Max job concurrency must be between 1 and 10."
                    )
            except (ValueError, TypeError) as exc:
                if "must be between" in str(exc):
                    raise
                raise ValueError(
                    "Max job concurrency must be a valid integer."
                ) from exc

        meta = KNOWN_SETTINGS.get(key, {})
        obj = await self._repo.upsert(
            key=key,
            value=value,
            description=str(meta.get("description", "")),
            is_secret=bool(meta.get("is_secret", False)),
            updated_by=actor,
        )

        restart = bool(meta.get("restart_required", False))
        log.info(
            "setting_updated",
            key=key,
            actor=actor,
            restart_required=restart,
        )

        return SettingResponse(
            key=obj.key,
            value=_mask_value(obj.value, obj.is_secret),
            description=obj.description,
            is_secret=obj.is_secret,
            updated_at=obj.updated_at,
            updated_by=obj.updated_by,
        )

    async def update_bulk(
        self, settings: dict[str, str], *, actor: str = "system"
    ) -> list[SettingResponse]:
        """Update multiple settings at once."""
        results: list[SettingResponse] = []
        for key, value in settings.items():
            result = await self.update_setting(key, value, actor=actor)
            results.append(result)
        return results

    def get_restart_required_keys(self) -> list[str]:
        """Return keys of settings that require a restart to take effect."""
        return [
            key
            for key, meta in KNOWN_SETTINGS.items()
            if meta.get("restart_required")
        ]
