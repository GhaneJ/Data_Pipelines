"""Reusable FastAPI authentication and role-authorization dependencies."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from backend.app.auth.models import AuthenticatedPrincipal, Role
from backend.app.auth.token_store import (
    ADMIN_TOKEN_HEADER,
    AuthConfigurationError,
    EnvironmentTokenStore,
    verify_admin_token,
)

AUTHORIZATION_HEADER = "Authorization"

_AUTHENTICATION_REQUIRED = "Authentication is required."
_MALFORMED_BEARER = "Use Authorization: Bearer <token>."
_INVALID_TOKEN = "Invalid authentication token."
_ADMIN_CONFIGURATION_ERROR = "Admin authentication is not configured."
_FORBIDDEN = "You do not have permission to access this resource."


def _unauthorized(message: str = _AUTHENTICATION_REQUIRED) -> HTTPException:
    """Build a safe 401 error without exposing credential details."""
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message)


def _forbidden() -> HTTPException:
    """Build a safe 403 error without exposing credential details."""
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_FORBIDDEN)


def _service_unavailable(message: str = _ADMIN_CONFIGURATION_ERROR) -> HTTPException:
    """Build a safe 503 error for server-side auth configuration problems."""
    return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=message)


def parse_bearer_token(authorization: str | None) -> str:
    """Extract a bearer token from the Authorization header.

    Missing, malformed, blank, and multi-part credentials all become safe 401
    errors. The raw token is returned only to the caller and is never logged or
    exposed in responses.
    """
    if authorization is None or not authorization.strip():
        raise _unauthorized()

    value = authorization.strip()
    parts = value.split()
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise _unauthorized(_MALFORMED_BEARER)
    return parts[1].strip()


def get_current_principal(
    authorization: Annotated[str | None, Header(alias=AUTHORIZATION_HEADER)] = None,
) -> AuthenticatedPrincipal:
    """Authenticate the current request from a standard bearer token."""
    token = parse_bearer_token(authorization)
    principal = EnvironmentTokenStore.from_environment().authenticate(token)
    if principal is None:
        raise _unauthorized(_INVALID_TOKEN)
    return principal


CurrentPrincipal = Annotated[AuthenticatedPrincipal, Depends(get_current_principal)]


def get_admin_compatible_principal(
    authorization: Annotated[str | None, Header(alias=AUTHORIZATION_HEADER)] = None,
    x_admin_token: Annotated[str | None, Header(alias=ADMIN_TOKEN_HEADER)] = None,
) -> AuthenticatedPrincipal:
    """Authenticate admin routes with bearer token first, legacy header second.

    When both headers are present, the standard Authorization bearer token is
    authoritative. The legacy X-Admin-Token bridge only accepts the configured
    admin token and exists for backward-compatible local admin-note workflows.
    """
    store = EnvironmentTokenStore.from_environment()
    try:
        store.require_admin_token_configured()
    except AuthConfigurationError as exc:
        raise _service_unavailable(str(exc)) from exc

    if authorization is not None and authorization.strip():
        return get_current_principal(authorization)

    if x_admin_token is None or not x_admin_token.strip():
        raise _unauthorized(_AUTHENTICATION_REQUIRED)

    try:
        principal = verify_admin_token(x_admin_token)
    except AuthConfigurationError as exc:
        raise _service_unavailable(str(exc)) from exc
    if principal is None:
        raise _unauthorized(_INVALID_TOKEN)
    return principal


AdminCompatibleCandidate = Annotated[AuthenticatedPrincipal, Depends(get_admin_compatible_principal)]


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
    """Require the admin role for standard bearer-authenticated routes."""
    if principal.role != Role.ADMIN:
        raise _forbidden()
    return principal


def require_provider(principal: CurrentPrincipal) -> AuthenticatedPrincipal:
    """Require the provider role for standard bearer-authenticated routes."""
    if principal.role != Role.PROVIDER:
        raise _forbidden()
    return principal


def require_admin_compatible(principal: AdminCompatibleCandidate) -> AuthenticatedPrincipal:
    """Require admin role while also accepting the legacy X-Admin-Token bridge."""
    if principal.role != Role.ADMIN:
        raise _forbidden()
    return principal


AdminPrincipal = Annotated[AuthenticatedPrincipal, Depends(require_admin)]
ProviderPrincipal = Annotated[AuthenticatedPrincipal, Depends(require_provider)]
AdminCompatiblePrincipal = Annotated[AuthenticatedPrincipal, Depends(require_admin_compatible)]
