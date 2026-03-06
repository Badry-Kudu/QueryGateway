"""Tests for settings and health dashboard — schemas, service, and API layer.

Integration tests (requiring PostgreSQL) are marked with @pytest.mark.integration.
"""


import pytest
from app.schemas.setting import SettingBulkUpdate, SettingResponse, SettingUpdate
from app.services.settings import KNOWN_SETTINGS, VALID_LOG_LEVELS, SettingsService

# ── Schema validation unit tests ─────────────────────────────────────────────


def test_setting_update_requires_value() -> None:
    payload = SettingUpdate(value="DEBUG")
    assert payload.value == "DEBUG"


def test_setting_update_rejects_empty() -> None:
    with pytest.raises(ValueError):
        SettingUpdate(value="")


def test_setting_bulk_update() -> None:
    payload = SettingBulkUpdate(settings={"log_level": "DEBUG", "query_timeout_seconds": "60"})
    assert len(payload.settings) == 2


def test_setting_response_fields() -> None:
    fields = SettingResponse.model_fields
    assert "key" in fields
    assert "value" in fields
    assert "description" in fields
    assert "is_secret" in fields
    assert "updated_at" in fields
    assert "updated_by" in fields


# ── Known settings unit tests ────────────────────────────────────────────────


def test_known_settings_have_defaults() -> None:
    for key, meta in KNOWN_SETTINGS.items():
        assert "default" in meta, f"Setting '{key}' missing 'default'."
        assert "description" in meta, f"Setting '{key}' missing 'description'."


def test_valid_log_levels() -> None:
    assert "DEBUG" in VALID_LOG_LEVELS
    assert "INFO" in VALID_LOG_LEVELS
    assert "WARNING" in VALID_LOG_LEVELS
    assert "ERROR" in VALID_LOG_LEVELS
    assert "CRITICAL" in VALID_LOG_LEVELS


def test_restart_required_keys() -> None:
    svc = SettingsService.__new__(SettingsService)
    keys = svc.get_restart_required_keys()
    assert "log_level" in keys
    assert "cors_origins" in keys
    assert "query_timeout_seconds" not in keys


# ── API integration tests (require PostgreSQL) ──────────────────────────────


@pytest.mark.integration
async def test_list_settings(async_client: object) -> None:
    from httpx import AsyncClient

    client: AsyncClient = async_client  # type: ignore[assignment]

    response = await client.get("/api/v1/admin/settings/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # Known settings should be seeded
    keys = {s["key"] for s in data}
    assert "log_level" in keys
    assert "query_timeout_seconds" in keys


@pytest.mark.integration
async def test_get_setting(async_client: object) -> None:
    from httpx import AsyncClient

    client: AsyncClient = async_client  # type: ignore[assignment]

    # Seed settings first
    await client.get("/api/v1/admin/settings/")

    response = await client.get("/api/v1/admin/settings/log_level")
    assert response.status_code == 200
    data = response.json()
    assert data["key"] == "log_level"


@pytest.mark.integration
async def test_get_setting_not_found(async_client: object) -> None:
    from httpx import AsyncClient

    client: AsyncClient = async_client  # type: ignore[assignment]

    response = await client.get("/api/v1/admin/settings/nonexistent_key")
    assert response.status_code == 404


@pytest.mark.integration
async def test_update_setting(async_client: object) -> None:
    from httpx import AsyncClient

    client: AsyncClient = async_client  # type: ignore[assignment]

    # Seed first
    await client.get("/api/v1/admin/settings/")

    response = await client.put(
        "/api/v1/admin/settings/log_level",
        json={"value": "DEBUG"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["value"] == "DEBUG"


@pytest.mark.integration
async def test_update_setting_invalid_log_level(async_client: object) -> None:
    from httpx import AsyncClient

    client: AsyncClient = async_client  # type: ignore[assignment]

    await client.get("/api/v1/admin/settings/")

    response = await client.put(
        "/api/v1/admin/settings/log_level",
        json={"value": "INVALID"},
    )
    assert response.status_code == 422
    assert "Invalid log level" in response.json()["detail"]


@pytest.mark.integration
async def test_update_setting_invalid_timeout(async_client: object) -> None:
    from httpx import AsyncClient

    client: AsyncClient = async_client  # type: ignore[assignment]

    await client.get("/api/v1/admin/settings/")

    response = await client.put(
        "/api/v1/admin/settings/query_timeout_seconds",
        json={"value": "999"},
    )
    assert response.status_code == 422
    assert "between 1 and 300" in response.json()["detail"]


@pytest.mark.integration
async def test_restart_required_keys_endpoint(async_client: object) -> None:
    from httpx import AsyncClient

    client: AsyncClient = async_client  # type: ignore[assignment]

    response = await client.get("/api/v1/admin/settings/restart-keys")
    assert response.status_code == 200
    keys = response.json()
    assert isinstance(keys, list)
    assert "log_level" in keys


@pytest.mark.integration
async def test_health_live(async_client: object) -> None:
    from httpx import AsyncClient

    client: AsyncClient = async_client  # type: ignore[assignment]

    response = await client.get("/api/v1/admin/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.integration
async def test_health_ready(async_client: object) -> None:
    from httpx import AsyncClient

    client: AsyncClient = async_client  # type: ignore[assignment]

    response = await client.get("/api/v1/admin/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["checks"]["db"] == "ok"


@pytest.mark.integration
async def test_health_dashboard(async_client: object) -> None:
    from httpx import AsyncClient

    client: AsyncClient = async_client  # type: ignore[assignment]

    response = await client.get("/api/v1/admin/health/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert "overall" in data
    assert "components" in data
    assert "scheduler" in data
    assert "recent_jobs" in data
    assert "stale_snapshots" in data
    assert data["components"]["database"]["status"] == "ok"
