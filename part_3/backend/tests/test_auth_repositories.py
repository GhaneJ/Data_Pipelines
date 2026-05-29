"""Repository-level tests for database-backed auth helpers."""

from __future__ import annotations

from datetime import timedelta

from backend.app.auth.models import Role
from backend.app.auth.password_hashing import hash_password
from backend.app.auth.repositories import (
    create_access_token_record,
    create_bootstrap_user,
    find_user_by_username,
    principal_from_user_row,
    resolve_access_token_hash,
    revoke_access_token_hash,
)
from backend.app.auth.tokens import hash_access_token, utc_now
from backend.tests.auth_test_utils import FakeAuthConnection


def test_create_and_find_bootstrap_user_without_raw_password_storage() -> None:
    conn = FakeAuthConnection()
    password_record = hash_password("admin-password")

    created = create_bootstrap_user(
        conn,
        username="Admin",
        display_name="Local Admin",
        role=Role.ADMIN,
        provider_id=None,
        password_config=password_record,
    )
    found = find_user_by_username(conn, "admin")

    assert found == created
    assert found["username"] == "admin"
    assert found["password_hash"] != "admin-password"
    assert found["password_salt"] != "admin-password"


def test_principal_from_user_row_contains_safe_identity_fields_only() -> None:
    conn = FakeAuthConnection()
    user = conn.add_user(username="provider", password="provider-password", role=Role.PROVIDER, provider_id="999999")

    principal = principal_from_user_row(user)

    assert principal.subject == f"user:{user['id']}"
    assert principal.username == "provider"
    assert principal.role == Role.PROVIDER
    assert principal.provider_id == "999999"
    assert "password" not in principal.model_dump_json()


def test_token_hash_can_resolve_active_token_and_reject_invalid_or_revoked() -> None:
    conn = FakeAuthConnection()
    user = conn.add_user(username="admin", password="admin-password", role=Role.ADMIN)
    raw_token = "raw-access-token"
    create_access_token_record(
        conn,
        user_id=user["id"],
        token_hash=hash_access_token(raw_token),
        expires_at=utc_now() + timedelta(hours=1),
    )

    resolved = resolve_access_token_hash(conn, token_hash=hash_access_token(raw_token))

    assert resolved is not None
    assert resolved["username"] == "admin"
    assert resolve_access_token_hash(conn, token_hash=hash_access_token("wrong")) is None
    assert revoke_access_token_hash(conn, token_hash=hash_access_token(raw_token)) is True
    assert resolve_access_token_hash(conn, token_hash=hash_access_token(raw_token))["revoked_at"] is not None
