"""Unit tests for centralized token authentication helpers."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from backend.app.auth.dependencies import parse_bearer_token, require_admin, require_provider
from backend.app.auth.models import AuthenticatedPrincipal, Role
from backend.app.auth.token_store import (
    ADMIN_TOKEN_ENV_VAR,
    PROVIDER_ID_ENV_VAR,
    PROVIDER_TOKEN_ENV_VAR,
    AuthConfigurationError,
    EnvironmentTokenStore,
    get_configured_admin_token,
    verify_admin_token,
)


def test_parse_bearer_token_accepts_standard_header() -> None:
    """The standard Authorization bearer format should extract only the token."""
    assert parse_bearer_token("Bearer local-secret") == "local-secret"
    assert parse_bearer_token("bearer local-secret") == "local-secret"


@pytest.mark.parametrize("header", [None, "", "Token local-secret", "Bearer", "Bearer one two"])
def test_parse_bearer_token_rejects_missing_or_malformed_header(header: str | None) -> None:
    """Malformed credentials should fail as 401, not become a fake principal."""
    with pytest.raises(HTTPException) as exc_info:
        parse_bearer_token(header)

    assert exc_info.value.status_code == 401


def test_environment_store_maps_admin_and_provider_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    """Configured tokens should map to safe principals without storing raw secrets."""
    monkeypatch.setenv(ADMIN_TOKEN_ENV_VAR, "admin-secret")
    monkeypatch.setenv(PROVIDER_TOKEN_ENV_VAR, "provider-secret")
    monkeypatch.setenv(PROVIDER_ID_ENV_VAR, "999999")

    store = EnvironmentTokenStore.from_environment()
    admin = store.authenticate("admin-secret")
    provider = store.authenticate("provider-secret")

    assert admin == AuthenticatedPrincipal(subject="local-admin", role=Role.ADMIN, provider_id=None)
    assert provider == AuthenticatedPrincipal(subject="local-provider", role=Role.PROVIDER, provider_id="999999")
    assert "admin-secret" not in admin.model_dump_json()
    assert "provider-secret" not in provider.model_dump_json()


def test_environment_store_rejects_unknown_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    """Invalid token values should not produce a principal."""
    monkeypatch.setenv(ADMIN_TOKEN_ENV_VAR, "admin-secret")
    monkeypatch.setenv(PROVIDER_TOKEN_ENV_VAR, "provider-secret")

    assert EnvironmentTokenStore.from_environment().authenticate("wrong") is None


def test_missing_admin_configuration_fails_clearly(monkeypatch: pytest.MonkeyPatch) -> None:
    """Admin-only compatibility paths should fail if no admin token is configured."""
    monkeypatch.delenv(ADMIN_TOKEN_ENV_VAR, raising=False)

    with pytest.raises(AuthConfigurationError) as exc_info:
        get_configured_admin_token()

    assert ADMIN_TOKEN_ENV_VAR in str(exc_info.value)


def test_verify_admin_token_returns_safe_principal() -> None:
    """The legacy admin-token helper should reuse the central principal model."""
    principal = verify_admin_token("expected", expected_token="expected")

    assert principal == AuthenticatedPrincipal(subject="local-admin", role=Role.ADMIN, provider_id=None)


def test_verify_admin_token_rejects_missing_or_wrong_token() -> None:
    """The helper should reject without exposing configured secrets."""
    assert verify_admin_token(None, expected_token="expected") is None
    assert verify_admin_token("wrong", expected_token="expected") is None


def test_role_dependencies_allow_matching_roles() -> None:
    """Reusable dependencies should return the principal when the role matches."""
    admin = AuthenticatedPrincipal(subject="local-admin", role=Role.ADMIN)
    provider = AuthenticatedPrincipal(subject="local-provider", role=Role.PROVIDER, provider_id="999999")

    assert require_admin(admin) == admin
    assert require_provider(provider) == provider


def test_role_dependencies_reject_wrong_roles() -> None:
    """Wrong role is authorization failure, not invalid authentication."""
    provider = AuthenticatedPrincipal(subject="local-provider", role=Role.PROVIDER, provider_id="999999")

    with pytest.raises(HTTPException) as exc_info:
        require_admin(provider)

    assert exc_info.value.status_code == 403
    assert "permission" in exc_info.value.detail
