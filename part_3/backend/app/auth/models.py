"""Authentication models used by backend dependencies and routes."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict


class Role(str, Enum):
    """Supported local API roles."""

    ADMIN = "admin"
    PROVIDER = "provider"


class AuthenticatedPrincipal(BaseModel):
    """A safe authenticated caller representation.

    The principal intentionally contains identity and authorization metadata,
    but never the raw token value that authenticated the request.
    """

    subject: str
    role: Role
    provider_id: str | None = None

    model_config = ConfigDict(use_enum_values=True)
