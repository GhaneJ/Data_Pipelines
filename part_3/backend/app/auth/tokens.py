"""Opaque access-token helpers for database-backed authentication."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta


ACCESS_TOKEN_BYTES = 32
ACCESS_TOKEN_TTL_HOURS = 8
TOKEN_HASH_ALGORITHM = "sha256"


def utc_now() -> datetime:
    """Return the current timezone-aware UTC timestamp."""
    return datetime.now(UTC)


def access_token_expiry(*, now: datetime | None = None, hours: int = ACCESS_TOKEN_TTL_HOURS) -> datetime:
    """Return the expiry timestamp for a new access token."""
    return (now or utc_now()) + timedelta(hours=hours)


def generate_access_token() -> str:
    """Generate a random opaque bearer token."""
    return secrets.token_urlsafe(ACCESS_TOKEN_BYTES)


def hash_access_token(raw_token: str) -> str:
    """Hash a raw bearer token before database storage or lookup."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def is_token_expired(expires_at: datetime, *, now: datetime | None = None) -> bool:
    """Return whether a token expiry timestamp is in the past."""
    current = now or utc_now()
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return expires_at <= current
