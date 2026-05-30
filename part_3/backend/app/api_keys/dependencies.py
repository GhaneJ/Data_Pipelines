"""FastAPI dependencies for X-API-Key machine authentication."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Any

import psycopg
from fastapi import Depends, Header, HTTPException, status

from backend.app.api_keys.key_utils import hash_api_key
from backend.app.api_keys.models import APIKeyPrincipal
from backend.app.api_keys.repositories import resolve_active_api_key_hash, update_api_key_last_used
from backend.app.dependencies import DatabaseConnection

API_KEY_HEADER = "X-API-Key"
_AUTHENTICATION_REQUIRED = "API key is required."
_MALFORMED_API_KEY = "Use X-API-Key: <api-key>."
_INVALID_API_KEY = "Invalid API key."
_FORBIDDEN = "API key does not have permission to access this resource."


def _unauthorized(message: str = _AUTHENTICATION_REQUIRED) -> HTTPException:
    """Build a safe API-key 401 error."""
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message)


def _forbidden() -> HTTPException:
    """Build a safe API-key 403 error."""
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_FORBIDDEN)


def parse_api_key_header(x_api_key: str | None) -> str:
    """Extract a raw API key from X-API-Key without logging it."""
    if x_api_key is None:
        raise _unauthorized()
    raw_api_key = x_api_key.strip()
    if not raw_api_key or any(char.isspace() for char in raw_api_key):
        raise _unauthorized(_MALFORMED_API_KEY)
    return raw_api_key


def api_key_principal_from_row(row: dict[str, Any]) -> APIKeyPrincipal:
    """Build a safe machine principal from an API key row."""
    return APIKeyPrincipal(
        subject=f"api_key:{row['id']}",
        api_key_id=str(row["id"]),
        name=row["name"],
        key_prefix=row["key_prefix"],
        scopes=list(row.get("scopes") or []),
        expires_at=row.get("expires_at"),
        created_by_user_id=str(row["created_by_user_id"]),
    )


def resolve_current_api_key_from_raw_key(
    conn: psycopg.Connection[dict[str, Any]],
    raw_api_key: str,
) -> APIKeyPrincipal:
    """Resolve a raw API key to a safe machine principal."""
    row = resolve_active_api_key_hash(conn, key_hash=hash_api_key(raw_api_key))
    if row is None:
        raise _unauthorized(_INVALID_API_KEY)
    update_api_key_last_used(conn, key_id=str(row["id"]))
    return api_key_principal_from_row(row)


def get_current_api_key_principal(
    conn: DatabaseConnection,
    x_api_key: Annotated[str | None, Header(alias=API_KEY_HEADER)] = None,
) -> APIKeyPrincipal:
    """Authenticate the request from X-API-Key."""
    raw_api_key = parse_api_key_header(x_api_key)
    return resolve_current_api_key_from_raw_key(conn, raw_api_key)


CurrentAPIKeyPrincipal = Annotated[APIKeyPrincipal, Depends(get_current_api_key_principal)]


def require_api_key_scope(scope: str) -> Callable[[CurrentAPIKeyPrincipal], APIKeyPrincipal]:
    """Return a dependency requiring one API key scope."""

    def dependency(principal: CurrentAPIKeyPrincipal) -> APIKeyPrincipal:
        if scope not in set(principal.scopes):
            raise _forbidden()
        return principal

    return dependency
