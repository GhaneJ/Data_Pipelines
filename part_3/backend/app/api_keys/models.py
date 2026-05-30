"""Pydantic models for database-backed API key management and resolution."""

from __future__ import annotations

from datetime import datetime
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

EXPORT_READ_SCOPE = "export:read"
STATS_READ_SCOPE = "stats:read"
REFRESH_RUN_SCOPE = "refresh:run"
ALLOWED_API_KEY_SCOPES = frozenset({EXPORT_READ_SCOPE, STATS_READ_SCOPE, REFRESH_RUN_SCOPE})
DEFAULT_API_KEY_SCOPES = [EXPORT_READ_SCOPE]


class APIKeyCreateRequest(BaseModel):
    """Payload used by admins to create a machine API key."""

    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    scopes: list[str] = Field(default_factory=lambda: list(DEFAULT_API_KEY_SCOPES), min_length=1, max_length=10)
    expires_in_days: int | None = Field(default=None, ge=1, le=3650)

    model_config = ConfigDict(extra="forbid")

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("name must not be blank")
        return cleaned

    @field_validator("description")
    @classmethod
    def clean_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("scopes")
    @classmethod
    def validate_scopes(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        for scope in value:
            normalized = scope.strip().lower()
            if normalized not in ALLOWED_API_KEY_SCOPES:
                allowed = ", ".join(sorted(ALLOWED_API_KEY_SCOPES))
                raise ValueError(f"Unsupported API key scope {scope!r}. Allowed scopes: {allowed}.")
            if normalized not in cleaned:
                cleaned.append(normalized)
        if not cleaned:
            raise ValueError("At least one API key scope is required.")
        return cleaned


class APIKeyCreateResponse(BaseModel):
    """API key creation response.

    The raw key is intentionally included only in this response. The database
    stores only the hash, and list/revoke models never include raw keys or
    hashes.
    """

    id: str
    name: str
    description: str | None = None
    key_prefix: str
    api_key: str
    scopes: list[str]
    expires_at: datetime | None = None
    created_at: datetime


class APIKeyListItem(BaseModel):
    """Safe API key metadata returned by admin list endpoints."""

    sensitive_fields_forbidden: ClassVar[frozenset[str]] = frozenset({"api_key", "key_hash"})

    id: str
    name: str
    description: str | None = None
    key_prefix: str
    scopes: list[str]
    is_active: bool
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    created_at: datetime
    last_used_at: datetime | None = None


class APIKeyRevokeResponse(BaseModel):
    """Response returned after an admin revokes an API key."""

    id: str
    revoked: bool


class APIKeyPrincipal(BaseModel):
    """Safe machine principal resolved from X-API-Key."""

    subject: str
    api_key_id: str
    name: str
    key_prefix: str
    scopes: list[str]
    expires_at: datetime | None = None
    created_by_user_id: str
