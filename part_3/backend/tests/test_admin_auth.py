"""Tests for the simple protected-admin token dependency."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from backend.app.security import ADMIN_TOKEN_ENV_VAR, require_admin_token, verify_admin_token


def test_missing_server_admin_token_returns_configuration_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Protected admin endpoints should be clearly unavailable until configured."""
    monkeypatch.delenv(ADMIN_TOKEN_ENV_VAR, raising=False)

    with pytest.raises(HTTPException) as exc_info:
        require_admin_token("anything")

    assert exc_info.value.status_code == 503
    assert ADMIN_TOKEN_ENV_VAR in exc_info.value.detail


def test_missing_request_admin_token_is_unauthorized(monkeypatch: pytest.MonkeyPatch) -> None:
    """A configured server token still requires the request header."""
    monkeypatch.setenv(ADMIN_TOKEN_ENV_VAR, "local-secret")

    with pytest.raises(HTTPException) as exc_info:
        require_admin_token(None)

    assert exc_info.value.status_code == 401
    assert "X-Admin-Token" in exc_info.value.detail


def test_wrong_request_admin_token_is_forbidden(monkeypatch: pytest.MonkeyPatch) -> None:
    """Wrong tokens should be rejected without exposing the expected value."""
    monkeypatch.setenv(ADMIN_TOKEN_ENV_VAR, "local-secret")

    with pytest.raises(HTTPException) as exc_info:
        require_admin_token("wrong-secret")

    assert exc_info.value.status_code == 403
    assert "Invalid admin token" in exc_info.value.detail
    assert "local-secret" not in exc_info.value.detail


def test_correct_request_admin_token_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    """The exact configured token should pass."""
    monkeypatch.setenv(ADMIN_TOKEN_ENV_VAR, "local-secret")

    assert require_admin_token("local-secret") == "local-secret"


def test_verify_admin_token_accepts_explicit_expected_token() -> None:
    """The pure helper is easy to test without environment variables."""
    assert verify_admin_token("expected", expected_token="expected") == "expected"
