"""AuthMethod service — business logic for auth configuration.

config_json shapes per method_type:
  bearer:  {"signing_secret_enc": "<fernet-b64>", "algorithm": "HS256", "expire_minutes": 60}
  basic:   {"username": "admin", "password_hash": "<bcrypt>"}
  api_key: {"key_hash": "<bcrypt>", "key_prefix": "db2api_"}

Secrets inside config_json are either Fernet-encrypted (bearer signing secret)
or bcrypt-hashed (basic password, api_key).  Neither is ever returned to callers.
"""

import base64
import hmac
import uuid
from collections.abc import Sequence
from datetime import datetime

import structlog

from app.auth.hashing import (
    generate_api_key,
    generate_signing_secret,
    hash_password,
    verify_password,
)
from app.auth.jwt_utils import TokenError, create_access_token, verify_access_token
from app.crypto import decrypt_password, encrypt_password
from app.models.auth_method import AuthMethod, AuthMethodType
from app.repositories.auth_method import AuthMethodRepository
from app.schemas.auth_method import (
    ApiKeyIssuedResponse,
    AuthMethodCreate,
    AuthMethodResponse,
    AuthMethodUpdate,
    RotateResponse,
    TokenIssuedResponse,
)

log = structlog.get_logger()


# ── config_json helpers ───────────────────────────────────────────────────────


def _encrypt_secret(plaintext: str) -> str:
    """Encrypt a signing secret and return as base64 string for JSON storage."""
    encrypted_bytes = encrypt_password(plaintext)
    return base64.b64encode(encrypted_bytes).decode()


def _decrypt_secret(enc_b64: str) -> str:
    """Decode and decrypt a stored signing secret."""
    encrypted_bytes = base64.b64decode(enc_b64.encode())
    return decrypt_password(encrypted_bytes)


def _build_config(payload: AuthMethodCreate) -> dict[str, object]:
    if payload.method_type == AuthMethodType.bearer:
        secret = generate_signing_secret()
        return {
            "signing_secret_enc": _encrypt_secret(secret),
            "algorithm": payload.algorithm,
            "expire_minutes": payload.expire_minutes,
        }
    if payload.method_type == AuthMethodType.basic:
        return {
            "username": payload.username,
            "password_hash": hash_password(payload.password or ""),
        }
    # api_key — key is generated separately so it can be returned once
    return {
        "key_hash": "",  # set by caller after generation
        "key_prefix": payload.key_prefix,
    }


def _to_response(obj: AuthMethod) -> AuthMethodResponse:
    cfg = obj.config_json
    return AuthMethodResponse(
        id=obj.id,
        name=obj.name,
        description=obj.description,
        method_type=obj.method_type,
        is_active=obj.is_active,
        algorithm=str(cfg["algorithm"]) if "algorithm" in cfg else None,
        expire_minutes=int(str(cfg["expire_minutes"])) if "expire_minutes" in cfg else None,
        username=str(cfg["username"]) if "username" in cfg else None,
        key_prefix=str(cfg["key_prefix"]) if "key_prefix" in cfg else None,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


# ── Service ───────────────────────────────────────────────────────────────────


class AuthMethodService:
    def __init__(self, repo: AuthMethodRepository) -> None:
        self._repo = repo

    async def list_auth_methods(
        self, *, active_only: bool = False
    ) -> Sequence[AuthMethodResponse]:
        rows = await self._repo.get_all(active_only=active_only)
        return [_to_response(r) for r in rows]

    async def get_auth_method(self, auth_id: uuid.UUID) -> AuthMethodResponse | None:
        obj = await self._repo.get_by_id(auth_id)
        return _to_response(obj) if obj else None

    async def create_auth_method(
        self, payload: AuthMethodCreate, *, actor: str = "system"
    ) -> tuple[AuthMethodResponse, ApiKeyIssuedResponse | None]:
        """Create an auth method.

        Returns (response, api_key_response).
        api_key_response is non-None only for api_key type — show once.
        """
        existing = await self._repo.get_by_name(payload.name)
        if existing:
            raise ValueError(f"An auth method named '{payload.name}' already exists.")

        config = _build_config(payload)
        plaintext_key: str | None = None

        if payload.method_type == AuthMethodType.api_key:
            prefix = str(config.get("key_prefix", "db2api_"))
            plaintext_key = generate_api_key(prefix)
            config["key_hash"] = hash_password(plaintext_key)

        obj = AuthMethod(
            name=payload.name,
            description=payload.description,
            method_type=payload.method_type,
            config_json=config,
            is_active=payload.is_active,
        )
        obj = await self._repo.create(obj)

        log.info(
            "auth_method_created",
            auth_method_id=str(obj.id),
            name=obj.name,
            method_type=obj.method_type,
            actor=actor,
        )

        key_response: ApiKeyIssuedResponse | None = None
        if plaintext_key is not None:
            key_response = ApiKeyIssuedResponse(api_key=plaintext_key)

        return _to_response(obj), key_response

    async def update_auth_method(
        self,
        auth_id: uuid.UUID,
        payload: AuthMethodUpdate,
        *,
        actor: str = "system",
    ) -> AuthMethodResponse | None:
        obj = await self._repo.get_by_id(auth_id)
        if obj is None:
            return None

        changes: dict[str, object] = {}

        if payload.name is not None and payload.name != obj.name:
            conflict = await self._repo.get_by_name(payload.name)
            if conflict:
                raise ValueError(f"An auth method named '{payload.name}' already exists.")
            changes["name"] = payload.name

        if payload.description is not None:
            changes["description"] = payload.description
        if payload.is_active is not None:
            changes["is_active"] = payload.is_active

        # Mutate config_json for type-specific updates
        config = dict(obj.config_json)
        config_changed = False

        if obj.method_type == AuthMethodType.bearer:
            if payload.expire_minutes is not None:
                config["expire_minutes"] = payload.expire_minutes
                config_changed = True

        if obj.method_type == AuthMethodType.basic:
            if payload.username is not None:
                config["username"] = payload.username
                config_changed = True
            if payload.password is not None:
                config["password_hash"] = hash_password(payload.password)
                config_changed = True

        if config_changed:
            changes["config_json"] = config

        obj = await self._repo.update(obj, changes)

        log.info(
            "auth_method_updated",
            auth_method_id=str(obj.id),
            name=obj.name,
            changed_fields=list(changes.keys()),
            actor=actor,
        )
        return _to_response(obj)

    async def delete_auth_method(
        self, auth_id: uuid.UUID, *, actor: str = "system"
    ) -> bool:
        obj = await self._repo.get_by_id(auth_id)
        if obj is None:
            return False
        name = obj.name
        await self._repo.delete(obj)
        log.info(
            "auth_method_deleted",
            auth_method_id=str(auth_id),
            name=name,
            actor=actor,
        )
        return True

    async def issue_token(
        self, auth_id: uuid.UUID, *, actor: str = "system"
    ) -> TokenIssuedResponse | None:
        """Issue a JWT for a bearer auth method. Returns None if not found."""
        obj = await self._repo.get_by_id(auth_id)
        if obj is None:
            return None
        if obj.method_type != AuthMethodType.bearer:
            raise ValueError("Token issuance is only available for bearer auth methods.")

        cfg = obj.config_json
        secret = _decrypt_secret(str(cfg["signing_secret_enc"]))
        algorithm = str(cfg.get("algorithm", "HS256"))
        expire_minutes = int(str(cfg.get("expire_minutes", 60)))

        token, expires_at = create_access_token(
            subject=obj.name,
            secret=secret,
            algorithm=algorithm,
            expire_minutes=expire_minutes,
        )
        log.info(
            "bearer_token_issued",
            auth_method_id=str(auth_id),
            name=obj.name,
            actor=actor,
        )
        return TokenIssuedResponse(token=token, expires_at=expires_at)

    async def rotate_credentials(
        self, auth_id: uuid.UUID, *, actor: str = "system"
    ) -> tuple[RotateResponse, ApiKeyIssuedResponse | None]:
        """Rotate secrets/keys.

        - bearer:  generates a new signing secret (old tokens immediately invalid).
        - api_key: generates a new key (returned once), old key immediately invalid.
        - basic:   not supported via rotate (use update with new password).

        Returns (RotateResponse, optional ApiKeyIssuedResponse).
        """
        obj = await self._repo.get_by_id(auth_id)
        if obj is None:
            raise ValueError("Auth method not found.")

        config = dict(obj.config_json)
        plaintext_key: str | None = None

        if obj.method_type == AuthMethodType.bearer:
            new_secret = generate_signing_secret()
            config["signing_secret_enc"] = _encrypt_secret(new_secret)
            message = (
                "Signing secret rotated. All previously issued tokens are now invalid. "
                "Issue new tokens."
            )

        elif obj.method_type == AuthMethodType.api_key:
            prefix = str(config.get("key_prefix", "db2api_"))
            plaintext_key = generate_api_key(prefix)
            config["key_hash"] = hash_password(plaintext_key)
            message = "API key rotated. The old key is now invalid."

        else:
            raise ValueError(
                "Rotation is not supported for basic auth. Use PUT to update the password."
            )

        await self._repo.update(obj, {"config_json": config})

        log.info(
            "auth_method_rotated",
            auth_method_id=str(auth_id),
            method_type=obj.method_type,
            actor=actor,
        )

        key_response = ApiKeyIssuedResponse(api_key=plaintext_key) if plaintext_key else None
        return RotateResponse(message=message), key_response

    # ── Verification helpers (used by data middleware in Phase 4) ─────────────

    async def verify_bearer(self, auth_id: uuid.UUID, token: str) -> str | None:
        """Verify a Bearer JWT. Returns token subject or None on failure."""
        obj = await self._repo.get_by_id(auth_id)
        if obj is None or obj.method_type != AuthMethodType.bearer:
            return None
        cfg = obj.config_json
        try:
            secret = _decrypt_secret(str(cfg["signing_secret_enc"]))
            payload = verify_access_token(
                token, secret=secret, algorithm=str(cfg.get("algorithm", "HS256"))
            )
            return str(payload.get("sub", ""))
        except (TokenError, Exception):
            return None

    async def verify_basic(
        self, auth_id: uuid.UUID, username: str, password: str
    ) -> bool:
        """Verify Basic auth credentials. Returns True on success."""
        obj = await self._repo.get_by_id(auth_id)
        if obj is None or obj.method_type != AuthMethodType.basic:
            return False
        cfg = obj.config_json
        stored_user = str(cfg.get("username", ""))
        stored_hash = str(cfg.get("password_hash", ""))
        # Run the bcrypt check and compare the username in constant time
        # regardless of whether the username matched (mirrors
        # app.auth.admin.authenticate_admin). An early return on a username
        # mismatch would leak — via response timing — which usernames exist,
        # enabling enumeration (L5).
        password_ok = verify_password(password, stored_hash) if stored_hash else False
        username_ok = hmac.compare_digest(username.encode(), stored_user.encode())
        return username_ok and password_ok

    async def verify_api_key(self, auth_id: uuid.UUID, key: str) -> bool:
        """Verify an API key. Returns True on success."""
        obj = await self._repo.get_by_id(auth_id)
        if obj is None or obj.method_type != AuthMethodType.api_key:
            return False
        cfg = obj.config_json
        stored_hash = str(cfg.get("key_hash", ""))
        return verify_password(key, stored_hash)

    # Type alias so callers get a typed datetime from issued_at
    _issued_at: datetime | None = None
