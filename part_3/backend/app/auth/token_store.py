"""Environment-backed token store for local project authentication."""

from __future__ import annotations

import os
import secrets

from backend.app.auth.models import AuthenticatedPrincipal, Role


ADMIN_TOKEN_ENV_VAR = "PART3_ADMIN_TOKEN"
PROVIDER_TOKEN_ENV_VAR = "PART3_PROVIDER_TOKEN"
PROVIDER_ID_ENV_VAR = "PART3_PROVIDER_ID"
ADMIN_TOKEN_HEADER = "X-Admin-Token"


class AuthConfigurationError(RuntimeError):
    """Raised when a protected role cannot be configured on the server."""


def _read_env(name: str) -> str | None:
    """Return a stripped environment value, or None when it is blank."""
    value = os.getenv(name, "").strip()
    return value or None


class EnvironmentTokenStore:
    """Map configured local tokens to safe authenticated principals."""

    def __init__(
        self,
        *,
        admin_token: str | None,
        provider_token: str | None,
        provider_id: str | None,
    ) -> None:
        self._admin_token = admin_token.strip() if admin_token else None
        self._provider_token = provider_token.strip() if provider_token else None
        self._provider_id = provider_id.strip() if provider_id else None

    @classmethod
    def from_environment(cls) -> "EnvironmentTokenStore":
        """Create a token store from current process environment variables."""
        return cls(
            admin_token=_read_env(ADMIN_TOKEN_ENV_VAR),
            provider_token=_read_env(PROVIDER_TOKEN_ENV_VAR),
            provider_id=_read_env(PROVIDER_ID_ENV_VAR),
        )

    @property
    def admin_configured(self) -> bool:
        """Return True when the local admin token is configured."""
        return bool(self._admin_token)

    def authenticate(self, token: str | None) -> AuthenticatedPrincipal | None:
        """Return the principal for a valid token, or None.

        Secrets are compared using constant-time comparison and are never
        included in the returned principal.
        """
        provided_token = token.strip() if token else ""
        if not provided_token:
            return None

        if self._admin_token and secrets.compare_digest(provided_token, self._admin_token):
            return AuthenticatedPrincipal(subject="local-admin", role=Role.ADMIN, provider_id=None)

        if self._provider_token and secrets.compare_digest(provided_token, self._provider_token):
            return AuthenticatedPrincipal(
                subject="local-provider",
                role=Role.PROVIDER,
                provider_id=self._provider_id,
            )

        return None

    def require_admin_token_configured(self) -> None:
        """Fail clearly when an admin-only route is enabled without a token."""
        if not self.admin_configured:
            raise AuthConfigurationError(
                f"{ADMIN_TOKEN_ENV_VAR} is not configured. Set it before using protected admin endpoints."
            )


def get_configured_admin_token() -> str:
    """Return the configured admin token for legacy checks and tests."""
    token = _read_env(ADMIN_TOKEN_ENV_VAR)
    if not token:
        raise AuthConfigurationError(
            f"{ADMIN_TOKEN_ENV_VAR} is not configured. Set it before using protected admin endpoints."
        )
    return token


def authenticate_token(token: str | None) -> AuthenticatedPrincipal | None:
    """Authenticate one raw token against the environment-backed store."""
    return EnvironmentTokenStore.from_environment().authenticate(token)


def verify_admin_token(provided_token: str | None, expected_token: str | None = None) -> AuthenticatedPrincipal | None:
    """Validate an admin token and return the admin principal.

    This helper exists for the compatibility header bridge and direct unit
    tests. Endpoint dependencies should use backend.app.auth.dependencies.
    """
    if expected_token is None:
        expected_token = get_configured_admin_token()
    expected = expected_token.strip() if expected_token else ""
    provided = provided_token.strip() if provided_token else ""

    if not expected:
        raise AuthConfigurationError(
            f"{ADMIN_TOKEN_ENV_VAR} is not configured. Set it before using protected admin endpoints."
        )
    if not provided:
        return None
    if not secrets.compare_digest(provided, expected):
        return None
    return AuthenticatedPrincipal(subject="local-admin", role=Role.ADMIN, provider_id=None)
