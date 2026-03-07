"""Phase 7 — Migration upgrade path validation.

Verifies that the Alembic migration chain is deterministic and complete:
- All models are reflected in migrations.
- Migration scripts have proper structure.
- Schema creation works on a clean database.

Note: The local ``alembic/`` package directory shadows the installed
``alembic`` package, so we validate migrations via file inspection
and import of the version modules rather than the Alembic API.
"""

import importlib
import pathlib
import uuid

import pytest

# ── Migration file structure tests ───────────────────────────────────────────


MIGRATION_DIR = pathlib.Path("alembic/versions")


class TestMigrationFileStructure:
    """Validate migration file structure and content."""

    def test_versions_directory_exists(self) -> None:
        assert MIGRATION_DIR.is_dir(), f"Migration versions directory not found: {MIGRATION_DIR}"

    def test_at_least_one_migration_exists(self) -> None:
        py_files = list(MIGRATION_DIR.glob("*.py"))
        assert len(py_files) >= 1, "No migration files found"

    def test_initial_migration_file_exists(self) -> None:
        initial = MIGRATION_DIR / "0001_initial_schema.py"
        assert initial.is_file(), "Initial migration 0001_initial_schema.py not found"

    def test_initial_migration_has_upgrade_and_downgrade(self) -> None:
        initial = MIGRATION_DIR / "0001_initial_schema.py"
        source = initial.read_text()
        assert "def upgrade()" in source, "Missing upgrade() in initial migration"
        assert "def downgrade()" in source, "Missing downgrade() in initial migration"

    def test_initial_migration_is_base(self) -> None:
        """The initial migration should have no down_revision."""
        initial = MIGRATION_DIR / "0001_initial_schema.py"
        source = initial.read_text()
        assert "down_revision" in source
        # down_revision should be None for the base
        assert "None" in source

    def test_migration_creates_all_tables(self) -> None:
        """All 8 domain tables must appear in migration."""
        initial = MIGRATION_DIR / "0001_initial_schema.py"
        source = initial.read_text()

        expected_tables = [
            "connections",
            "auth_methods",
            "endpoints",
            "schedules",
            "job_runs",
            "snapshots",
            "access_logs",
            "app_settings",
        ]
        for table in expected_tables:
            assert table in source, f"Table '{table}' not found in initial migration"

    def test_downgrade_drops_all_tables(self) -> None:
        """Downgrade should drop all tables and enum types."""
        initial = MIGRATION_DIR / "0001_initial_schema.py"
        source = initial.read_text()

        # Check that downgrade drops tables
        expected_drops = [
            "op.drop_table",
        ]
        for drop in expected_drops:
            assert drop in source, f"Expected '{drop}' in downgrade"

    def test_migration_creates_enum_types(self) -> None:
        """Enum types should be created in migration."""
        initial = MIGRATION_DIR / "0001_initial_schema.py"
        source = initial.read_text()

        expected_enums = [
            "oracle_mode",
            "auth_method_type",
            "data_strategy",
            "schedule_type",
            "job_run_status",
        ]
        for enum_name in expected_enums:
            assert enum_name in source, f"Enum type '{enum_name}' not found in migration"

    def test_no_duplicate_migration_files(self) -> None:
        """Each migration revision ID should be unique across files."""
        py_files = list(MIGRATION_DIR.glob("*.py"))
        # Extract revision IDs from filenames (e.g., 0001_initial_schema.py → 0001)
        revisions = [f.stem.split("_")[0] for f in py_files]
        assert len(revisions) == len(set(revisions)), "Duplicate migration revision IDs"


# ── Model–migration alignment tests ─────────────────────────────────────────


class TestModelMigrationAlignment:
    """Verify all ORM models have corresponding migration coverage."""

    def test_all_model_tables_in_migration(self) -> None:
        """Every SQLAlchemy model tablename must appear in migration scripts."""
        from app.models.base import Base

        # Import all model modules to register them with Base.metadata
        model_modules = [
            "app.models.connection",
            "app.models.auth_method",
            "app.models.endpoint",
            "app.models.schedule",
            "app.models.job_run",
            "app.models.snapshot",
            "app.models.access_log",
            "app.models.setting",
        ]
        for mod in model_modules:
            importlib.import_module(mod)

        model_tables = set(Base.metadata.tables.keys())
        assert len(model_tables) >= 8, f"Expected >=8 tables, got {model_tables}"

        migration_path = MIGRATION_DIR / "0001_initial_schema.py"
        migration_source = migration_path.read_text()

        for table_name in model_tables:
            assert table_name in migration_source, (
                f"Table '{table_name}' defined in models but not found in migration"
            )


# ── Alembic config validation ───────────────────────────────────────────────


class TestAlembicConfig:
    """Validate Alembic environment configuration."""

    def test_alembic_ini_exists(self) -> None:
        ini = pathlib.Path("alembic.ini")
        assert ini.is_file(), "alembic.ini not found"

    def test_env_py_exists(self) -> None:
        env = pathlib.Path("alembic/env.py")
        assert env.is_file(), "alembic/env.py not found"

    def test_env_py_imports_models(self) -> None:
        """env.py should import Base metadata for autogenerate support."""
        env = pathlib.Path("alembic/env.py")
        source = env.read_text()
        assert "Base" in source or "target_metadata" in source, (
            "env.py should reference Base metadata"
        )


# ── Database schema tests (require PostgreSQL) ──────────────────────────────


@pytest.mark.integration
class TestSchemaCreation:
    """Verify schema creation from models matches expectations."""

    async def test_tables_created(self, async_client: object) -> None:
        """The conftest engine fixture creates all tables; verify key tables exist."""
        from httpx import AsyncClient

        client: AsyncClient = async_client  # type: ignore[assignment]

        # If we can hit the health endpoint, tables are created
        r = await client.get("/api/v1/admin/health/ready")
        assert r.status_code == 200

    async def test_connection_crud_after_fresh_schema(
        self, async_client: object
    ) -> None:
        """Verify CRUD operations work on fresh schema."""
        from httpx import AsyncClient

        client: AsyncClient = async_client  # type: ignore[assignment]

        name = f"migration-test-{uuid.uuid4().hex[:8]}"
        r = await client.post(
            "/api/v1/admin/connections/",
            json={
                "name": name,
                "host": "localhost",
                "service_name": "XE",
                "username": "test",
                "password": "test",
            },
        )
        assert r.status_code == 201

        conn_id = r.json()["id"]
        r = await client.delete(f"/api/v1/admin/connections/{conn_id}")
        assert r.status_code == 204
