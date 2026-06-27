"""Application configuration via Pydantic Settings v2."""

from cryptography.fernet import Fernet
from pydantic import Field, field_validator
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

    @field_validator("cors_origins")
    @classmethod
    def _reject_wildcard_origin(cls, value: str) -> str:
        """Refuse to boot with a wildcard CORS origin (M3).

        The app sends ``allow_credentials=True``; under credentials a
        wildcard origin makes CORSMiddleware reflect *any* Origin, which is
        a cross-origin data-theft vector (§3.7). Fail fast at startup rather
        than silently shipping an unsafe policy. List explicit origins.
        """
        origins = [o.strip() for o in value.split(",") if o.strip()]
        if any(o == "*" for o in origins):
            raise ValueError(
                "CORS_ORIGINS must not be or contain '*': the app sends "
                "allow_credentials=True, so a wildcard origin would reflect any "
                "Origin and leak credentialed responses cross-site. List "
                "explicit origins instead."
            )
        return value

    # JWT — signing key MUST be provided via environment.
    # No default is set to avoid shipping a known signing key.
    # min_length=32 rejects empty / dangerously short values at startup so
    # tokens can't be forged via low-entropy keys.
    jwt_secret_key: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    # Seeded admin credentials — REQUIRED.
    # The app supports a single admin account whose username and bcrypt
    # password hash are supplied via environment variables. There is no
    # users table; rotating the credential means redeploying with a new
    # ADMIN_PASSWORD_HASH. Generate the hash with:
    #   python -c "from app.auth.hashing import hash_password; \
    #              print(hash_password('your-password'))"
    admin_username: str = Field(min_length=1)
    admin_password_hash: str = Field(min_length=1)

    @field_validator("admin_password_hash")
    @classmethod
    def _validate_bcrypt_hash(cls, value: str) -> str:
        """Reject ADMIN_PASSWORD_HASH values that are not valid bcrypt
        hashes at startup, rather than producing 500s on every login.

        bcrypt's checkpw raises ``ValueError`` on malformed input (plaintext,
        wrong scheme, truncated digest, etc.). Probing once with a dummy
        password gives us a clear startup failure with actionable guidance
        instead of a runtime DoS.
        """
        import bcrypt  # local import to avoid widening config.py imports

        try:
            bcrypt.checkpw(b"probe", value.encode())
        except ValueError as exc:
            raise ValueError(
                "ADMIN_PASSWORD_HASH must be a bcrypt hash. Generate with: "
                'python -c "from app.auth.hashing import hash_password; '
                "print(hash_password('your-password'))\""
            ) from exc
        return value

    # Logging
    log_level: str = "INFO"

    # Query execution
    query_timeout_seconds: int = 30

    # Credential encryption — Fernet key (base64-encoded 32-byte key).
    # To generate:
    #   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    # MUST be provided via environment; no default is set to avoid shipping a known key.
    encryption_key: str

    @field_validator("encryption_key")
    @classmethod
    def _validate_fernet_key(cls, value: str) -> str:
        """Reject empty or malformed Fernet keys at startup, rather than
        letting `Fernet(...)` fail on the first encrypt/decrypt call."""
        try:
            Fernet(value.encode())
        except (ValueError, TypeError) as exc:
            raise ValueError(
                "ENCRYPTION_KEY must be a valid Fernet key (urlsafe-base64-"
                "encoded 32 bytes). Generate with: python -c \"from "
                "cryptography.fernet import Fernet; "
                "print(Fernet.generate_key().decode())\""
            ) from exc
        return value

    # Oracle Instant Client path — required only when using thick mode connections.
    # Example: C:\oracle\instantclient_23_0 (Windows) or /opt/oracle/instantclient_23_0 (Linux)
    oracle_client_lib_dir: str = ""


settings = Settings()
