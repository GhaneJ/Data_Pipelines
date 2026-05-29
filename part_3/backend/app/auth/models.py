"""Authentication models used by backend dependencies and routes."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class Role(str, Enum):
    """Supported local API roles."""

    ADMIN = "admin"
    PROVIDER = "provider"


class AuthenticatedPrincipal(BaseModel):
    """Safe authenticated caller representation.

    The principal intentionally contains identity and authorization metadata,
    but never passwords, password hashes, salts, raw access tokens, or token
    hashes.
    """

    subject: str
    username: str
    display_name: str
    role: Role
    provider_id: str | None = None

    model_config = ConfigDict(use_enum_values=True)


class LoginRequest(BaseModel):
    """Credentials submitted to create a database-backed login session."""

    username: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=1, max_length=500)


class LoginResponse(BaseModel):
    """Successful login response.

    The raw access token is returned once here. Only its hash is stored in the
    database.
    """

    access_token: str
    token_type: str = "bearer"
    expires_at: datetime


class WhoamiResponse(AuthenticatedPrincipal):
    """Safe current-user response returned by /auth/whoami."""


class LogoutResponse(BaseModel):
    """Safe logout response after revoking the current access token."""

    revoked: bool
