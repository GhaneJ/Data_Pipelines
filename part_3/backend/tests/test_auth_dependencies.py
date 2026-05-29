"""Unit tests for centralized database-backed auth dependencies."""

from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi import HTTPException

from backend.app.auth.dependencies import parse_bearer_token, require_admin, require_provider, resolve_current_principal_from_token
from backend.app.auth.models import AuthenticatedPrincipal, Role
from backend.app.auth.tokens import utc_now
from backend.tests.auth_test_utils import FakeAuthConnection


def test_parse_bearer_token_accepts_standard_header() -> None:
    assert parse_bearer_token("Bearer local-secret") == "local-secret"
    assert parse_bearer_token("bearer local-secret") == "local-secret"


@pytest.mark.parametrize("header", [None, "", "Token local-secret", "Bearer", "Bearer one two"])
def test_parse_bearer_token_rejects_missing_or_malformed_header(header: str | None) -> None:
    with pytest.raises(HTTPException) as exc_info:
        parse_bearer_token(header)

    assert exc_info.value.status_code == 401


def test_resolve_current_principal_from_active_database_token() -> None:
    conn = FakeAuthConnection()
    user = conn.add_user(username="admin", password="admin-password", role=Role.ADMIN, display_name="Local Admin")
    conn.add_token(username="admin", raw_token="valid-token")

    principal = resolve_current_principal_from_token(conn, "valid-token")

    assert principal == AuthenticatedPrincipal(
        subject=f"user:{user['id']}",
        username="admin",
        display_name="Local Admin",
        role=Role.ADMIN,
        provider_id=None,
    )
    assert "valid-token" not in principal.model_dump_json()


@pytest.mark.parametrize(
    "setup_token",
    [
        lambda conn: None,
        lambda conn: conn.add_token(username="admin", raw_token="valid-token", revoked=True),
        lambda conn: conn.add_token(username="admin", raw_token="valid-token", expires_at=utc_now() - timedelta(minutes=1)),
    ],
)
def test_resolve_current_principal_rejects_invalid_revoked_or_expired_tokens(setup_token) -> None:
    conn = FakeAuthConnection()
    conn.add_user(username="admin", password="admin-password", role=Role.ADMIN)
    setup_token(conn)

    with pytest.raises(HTTPException) as exc_info:
        resolve_current_principal_from_token(conn, "valid-token")

    assert exc_info.value.status_code == 401


def test_resolve_current_principal_rejects_inactive_or_locked_users() -> None:
    inactive = FakeAuthConnection()
    inactive.add_user(username="admin", password="admin-password", role=Role.ADMIN, is_active=False)
    inactive.add_token(username="admin", raw_token="inactive-token")

    with pytest.raises(HTTPException) as inactive_exc:
        resolve_current_principal_from_token(inactive, "inactive-token")
    assert inactive_exc.value.status_code == 401

    locked = FakeAuthConnection()
    locked.add_user(
        username="admin",
        password="admin-password",
        role=Role.ADMIN,
        locked_until=utc_now() + timedelta(minutes=10),
    )
    locked.add_token(username="admin", raw_token="locked-token")

    with pytest.raises(HTTPException) as locked_exc:
        resolve_current_principal_from_token(locked, "locked-token")
    assert locked_exc.value.status_code == 401


def test_role_dependencies_allow_matching_roles() -> None:
    admin = AuthenticatedPrincipal(subject="user:1", username="admin", display_name="Admin", role=Role.ADMIN)
    provider = AuthenticatedPrincipal(
        subject="user:2",
        username="provider",
        display_name="Provider",
        role=Role.PROVIDER,
        provider_id="999999",
    )

    assert require_admin(admin) == admin
    assert require_provider(provider) == provider


def test_role_dependencies_reject_wrong_roles() -> None:
    provider = AuthenticatedPrincipal(
        subject="user:2",
        username="provider",
        display_name="Provider",
        role=Role.PROVIDER,
        provider_id="999999",
    )

    with pytest.raises(HTTPException) as exc_info:
        require_admin(provider)

    assert exc_info.value.status_code == 403
    assert "permission" in exc_info.value.detail
