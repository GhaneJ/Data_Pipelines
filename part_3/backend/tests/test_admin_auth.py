"""Tests for admin-route token support."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from backend.app.auth.dependencies import get_admin_route_principal
from backend.app.auth.models import AuthenticatedPrincipal, Role
from backend.app.auth.token_store import ADMIN_TOKEN_ENV_VAR, verify_admin_header_token


def test_missing_server_admin_token_returns_configuration_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Protected admin endpoints should be clearly unavailable until configured."""
    monkeypatch.delenv(ADMIN_TOKEN_ENV_VAR, raising=False)

    with pytest.raises(HTTPException) as exc_info:
        get_admin_route_principal(x_admin_token="anything")

    assert exc_info.value.status_code == 503
    assert ADMIN_TOKEN_ENV_VAR in exc_info.value.detail


def test_missing_request_admin_token_is_unauthorized(monkeypatch: pytest.MonkeyPatch) -> None:
    """A configured server token still requires request credentials."""
    monkeypatch.setenv(ADMIN_TOKEN_ENV_VAR, "local-secret")

    with pytest.raises(HTTPException) as exc_info:
        get_admin_route_principal()

    assert exc_info.value.status_code == 401
    assert "Authentication is required" in exc_info.value.detail


def test_wrong_request_admin_token_is_unauthorized(monkeypatch: pytest.MonkeyPatch) -> None:
    """Wrong tokens should be rejected without exposing the expected value."""
    monkeypatch.setenv(ADMIN_TOKEN_ENV_VAR, "local-secret")

    with pytest.raises(HTTPException) as exc_info:
        get_admin_route_principal(x_admin_token="wrong-secret")

    assert exc_info.value.status_code == 401
    assert "Invalid authentication token" in exc_info.value.detail
    assert "local-secret" not in exc_info.value.detail


def test_correct_request_admin_token_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    """The exact configured token should return the safe admin principal."""
    monkeypatch.setenv(ADMIN_TOKEN_ENV_VAR, "local-secret")

    assert get_admin_route_principal(x_admin_token="local-secret") == AuthenticatedPrincipal(
        subject="local-admin",
        role=Role.ADMIN,
        provider_id=None,
    )


def test_verify_admin_header_token_accepts_explicit_expected_token() -> None:
    """The pure helper is easy to test without environment variables."""
    assert verify_admin_header_token("expected", expected_token="expected") == AuthenticatedPrincipal(
        subject="local-admin",
        role=Role.ADMIN,
        provider_id=None,
    )
