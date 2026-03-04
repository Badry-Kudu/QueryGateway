"""Application configuration via Pydantic Settings v2."""

from pydantic import field_validator
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

    # CORS
    cors_origins: list[str] = ["http://localhost:5173"]

    # JWT
    jwt_secret_key: str = "changeme-use-a-real-secret-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    # Logging
    log_level: str = "INFO"

    # Query execution
    query_timeout_seconds: int = 30

    # Credential encryption — Fernet key (base64-encoded 32-byte key).
    # To generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key())"
    # MUST be set in production; the default is dev-only.
    encryption_key: str = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v


settings = Settings()
