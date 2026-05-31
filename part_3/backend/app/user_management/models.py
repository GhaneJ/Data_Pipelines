"""Models for controlled provider signup and admin user management."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.auth.models import Role

MAX_TEXT_LENGTH = 500
MAX_NOTES_LENGTH = 4000


class RegistrationRequestStatus(str, Enum):
    """Controlled provider access-request states."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class RegistrationRequestCreateRequest(BaseModel):
    """Public request for provider access.

    Public signup is intentionally limited to provider access requests. It
    stores a pending request and never creates an active user immediately.
    """

    requested_username: str = Field(min_length=1, max_length=200)
    display_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=8, max_length=500)
    provider_id: str = Field(min_length=1, max_length=100)
    requested_role: Role = Role.PROVIDER
    email: str | None = Field(default=None, max_length=320)
    organization_name: str | None = Field(default=None, max_length=MAX_TEXT_LENGTH)
    message: str | None = Field(default=None, max_length=MAX_NOTES_LENGTH)

    model_config = ConfigDict(extra="forbid", use_enum_values=True)

    @field_validator("requested_username", "display_name", "provider_id", "organization_name", "message", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("requested_username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not cleaned:
            raise ValueError("requested_username must not be blank")
        return cleaned

    @field_validator("requested_role")
    @classmethod
    def provider_only(cls, value: Role) -> Role:
        if Role(value) != Role.PROVIDER:
            raise ValueError("Public signup can request provider access only.")
        return Role.PROVIDER

    @field_validator("organization_name", "message")
    @classmethod
    def blank_optional_text_becomes_none(cls, value: str | None) -> str | None:
        if value == "":
            return None
        return value


class RegistrationRequestReviewRequest(BaseModel):
    """Admin review note for approve/reject operations."""

    review_notes: str | None = Field(default=None, max_length=MAX_NOTES_LENGTH)

    model_config = ConfigDict(extra="forbid")

    @field_validator("review_notes", mode="before")
    @classmethod
    def strip_notes(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("review_notes")
    @classmethod
    def blank_notes_become_none(cls, value: str | None) -> str | None:
        return None if value == "" else value


class RegistrationRequestResponse(BaseModel):
    """Safe registration-request response without password hashes."""

    id: UUID
    requested_username: str
    display_name: str
    email: str | None = None
    provider_id: str
    requested_role: Role
    organization_name: str | None = None
    message: str | None = None
    status: RegistrationRequestStatus
    created_at: datetime
    reviewed_by_user_id: UUID | None = None
    reviewed_at: datetime | None = None
    review_notes: str | None = None
    created_user_id: UUID | None = None

    model_config = ConfigDict(use_enum_values=True)


class RegistrationRequestListResponse(BaseModel):
    """Paginated admin list of registration requests."""

    items: list[RegistrationRequestResponse]
    limit: int
    offset: int


class ManagedUserResponse(BaseModel):
    """Safe admin-visible user model."""

    id: UUID
    username: str
    display_name: str
    role: Role
    provider_id: str | None = None
    is_active: bool
    failed_login_count: int
    locked_until: datetime | None = None
    last_login_at: datetime | None = None
    password_changed_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(use_enum_values=True)


class ManagedUserListResponse(BaseModel):
    """Paginated admin user list response."""

    items: list[ManagedUserResponse]
    limit: int
    offset: int


class ManagedUserCreateRequest(BaseModel):
    """Admin payload for creating an active user."""

    username: str = Field(min_length=1, max_length=200)
    display_name: str = Field(min_length=1, max_length=200)
    role: Role
    password: str = Field(min_length=8, max_length=500)
    provider_id: str | None = Field(default=None, max_length=100)
    is_active: bool = True

    model_config = ConfigDict(extra="forbid", use_enum_values=True)

    @field_validator("username", "display_name", "provider_id", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not cleaned:
            raise ValueError("username must not be blank")
        return cleaned


class ManagedUserUpdateRequest(BaseModel):
    """Admin payload for safe profile/role/status updates."""

    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    role: Role | None = None
    provider_id: str | None = Field(default=None, max_length=100)
    is_active: bool | None = None

    model_config = ConfigDict(extra="forbid", use_enum_values=True)

    @field_validator("display_name", "provider_id", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value


class PasswordResetRequest(BaseModel):
    """Admin payload for resetting a password."""

    new_password: str = Field(min_length=8, max_length=500)
    revoke_existing_sessions: bool = True

    model_config = ConfigDict(extra="forbid")


class UserActionResponse(BaseModel):
    """Small response for user state-changing actions."""

    id: UUID
    changed: bool


class SessionResponse(BaseModel):
    """Safe user session metadata returned to admins."""

    id: UUID
    user_id: UUID
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None
    last_used_at: datetime | None = None
    is_active: bool


class SessionListResponse(BaseModel):
    """Admin response for one user's bearer sessions."""

    items: list[SessionResponse]


class SessionRevokeResponse(BaseModel):
    """Response after revoking a bearer session."""

    id: UUID
    revoked: bool
