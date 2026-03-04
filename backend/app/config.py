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

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, v: str | list[str]) -> list[str]:
        # Normalize CORS origins from env:
        # - support comma-separated strings
        # - strip whitespace
        # - drop empty entries
        # - deduplicate while preserving order
        def _normalize(origins: list[str]) -> list[str]:
            seen: set[str] = set()
            normalized: list[str] = []
            for origin in origins:
                if origin is None:
                    continue
                origin_str = origin.strip()
                if not origin_str:
                    continue
                if origin_str in seen:
                    continue
                seen.add(origin_str)
                normalized.append(origin_str)
            return normalized

        if isinstance(v, str):
            return _normalize(v.split(","))
        if isinstance(v, list):
            return _normalize(v)
        return v


settings = Settings()
