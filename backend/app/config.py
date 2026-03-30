"""Application configuration via Pydantic Settings v2."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_env: str = "development"
    debug: bool = False

    # Database (PostgreSQL)
    database_url: str = "postgresql+asyncpg://db2api:db2api@localhost:5432/db2api"

    # CORS — comma-separated string in .env, e.g.: CORS_ORIGINS=http://localhost:5173,http://localhost:3000
    # Stored as str to avoid pydantic-settings JSON pre-parsing a plain comma-separated value.
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # JWT
    jwt_secret_key: str = "changeme-use-a-real-secret-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    # Logging
    log_level: str = "INFO"

    # Query execution
    query_timeout_seconds: int = 30

    # Credential encryption — Fernet key (base64-encoded 32-byte key).
    # To generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    # MUST be provided via environment; no default is set to avoid shipping a known key.
    encryption_key: str

    # Oracle Instant Client path — required only when using thick mode connections.
    # Example: C:\oracle\instantclient_23_0 (Windows) or /opt/oracle/instantclient_23_0 (Linux)
    oracle_client_lib_dir: str = ""


settings = Settings()
