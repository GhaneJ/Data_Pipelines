"""Reusable FastAPI authentication and role-authorization dependencies."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC
from typing import Annotated, Any

import psycopg
from fastapi import Depends, Header, HTTPException, status

from backend.app.auth.models import AuthenticatedPrincipal, Role
from backend.app.auth.repositories import principal_from_user_row, resolve_access_token_hash, update_token_last_used
from backend.app.auth.tokens import hash_access_token, is_token_expired
from backend.app.dependencies import DatabaseConnection

AUTHORIZATION_HEADER = "Authorization"

_AUTHENTICATION_REQUIRED = "Authentication is required."
_MALFORMED_BEARER = "Use Authorization: Bearer <token>."
_INVALID_TOKEN = "Invalid authentication token."
_INACTIVE_USER = "Authentication is not available for this user."
_LOCKED_USER = "Authentication is temporarily unavailable for this user."
_FORBIDDEN = "You do not have permission to access this resource."


def _unauthorized(message: str = _AUTHENTICATION_REQUIRED) -> HTTPException:
    """Build a safe 401 error without exposing credential details."""
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message)


def _forbidden() -> HTTPException:
    """Build a safe 403 error without exposing credential details."""
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_FORBIDDEN)


def parse_bearer_token(authorization: str | None) -> str:
    """Extract a bearer token from the Authorization header.

    Missing, malformed, blank, and multi-part credentials all become safe 401
    errors. The raw token is returned only to the caller and is never logged or
    exposed in responses.
    """
    if authorization is None or not authorization.strip():
        raise _unauthorized()

    parts = authorization.strip().split()
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise _unauthorized(_MALFORMED_BEARER)
    return parts[1].strip()


def _is_locked(row: dict[str, Any]) -> bool:
    locked_until = row.get("locked_until")
    if locked_until is None:
        return False
    if locked_until.tzinfo is None:
        locked_until = locked_until.replace(tzinfo=UTC)
    from backend.app.auth.tokens import utc_now

    return locked_until > utc_now()


def resolve_current_principal_from_token(
    conn: psycopg.Connection[dict[str, Any]],
    raw_token: str,
) -> AuthenticatedPrincipal:
    """Resolve a raw bearer token to a safe database-backed principal."""
    token_hash = hash_access_token(raw_token)
    row = resolve_access_token_hash(conn, token_hash=token_hash)
    if row is None:
        raise _unauthorized(_INVALID_TOKEN)
    if row.get("revoked_at") is not None:
        raise _unauthorized(_INVALID_TOKEN)
    if is_token_expired(row["expires_at"]):
        raise _unauthorized(_INVALID_TOKEN)
    if not row.get("is_active", False):
        raise _unauthorized(_INACTIVE_USER)
    if _is_locked(row):
        raise _unauthorized(_LOCKED_USER)

    update_token_last_used(conn, token_id=str(row["token_id"]))
    return principal_from_user_row(row)


def get_current_principal(
    conn: DatabaseConnection,
    authorization: Annotated[str | None, Header(alias=AUTHORIZATION_HEADER)] = None,
) -> AuthenticatedPrincipal:
    """Authenticate the current request from a database-issued bearer token."""
    token = parse_bearer_token(authorization)
    return resolve_current_principal_from_token(conn, token)


CurrentPrincipal = Annotated[AuthenticatedPrincipal, Depends(get_current_principal)]


def require_role(*roles: Role) -> Callable[[CurrentPrincipal], AuthenticatedPrincipal]:
    """Return a dependency function requiring one of the supplied roles."""
    allowed_roles = set(roles)

    def dependency(principal: CurrentPrincipal) -> AuthenticatedPrincipal:
        if principal.role not in allowed_roles:
            raise _forbidden()
        return principal

    return dependency


def require_any_role(principal: CurrentPrincipal) -> AuthenticatedPrincipal:
    """Return any valid authenticated principal."""
    return principal


def require_admin(principal: CurrentPrincipal) -> AuthenticatedPrincipal:
    """Require the admin role for bearer-authenticated routes."""
    if principal.role != Role.ADMIN:
        raise _forbidden()
    return principal


def require_provider(principal: CurrentPrincipal) -> AuthenticatedPrincipal:
    """Require the provider role for bearer-authenticated routes."""
    if principal.role != Role.PROVIDER:
        raise _forbidden()
    return principal


AdminPrincipal = Annotated[AuthenticatedPrincipal, Depends(require_admin)]
ProviderPrincipal = Annotated[AuthenticatedPrincipal, Depends(require_provider)]
AdminRoutePrincipal = AdminPrincipal
