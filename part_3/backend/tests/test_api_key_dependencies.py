"""Dependency tests for X-API-Key authentication and scopes."""

from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi import HTTPException

from backend.app.api_keys.dependencies import parse_api_key_header, require_api_key_scope, resolve_current_api_key_from_raw_key
from backend.app.api_keys.models import APIKeyPrincipal, EXPORT_READ_SCOPE
from backend.app.auth.tokens import utc_now
from backend.tests.auth_test_utils import FakeAuthConnection


def test_parse_api_key_header_accepts_single_opaque_value() -> None:
    assert parse_api_key_header(" part3_secret ") == "part3_secret"


@pytest.mark.parametrize("header", [None, "", "   ", "part3_one two"])
def test_parse_api_key_header_rejects_missing_blank_or_malformed(header: str | None) -> None:
    with pytest.raises(HTTPException) as exc_info:
        parse_api_key_header(header)

    assert exc_info.value.status_code == 401


def test_resolve_current_api_key_from_raw_key_returns_safe_principal() -> None:
    conn = FakeAuthConnection()
    raw_key = "part3_valid_export_client_secret_value"
    row = conn.add_api_key(raw_api_key=raw_key, name="Export client", scopes=[EXPORT_READ_SCOPE])

    principal = resolve_current_api_key_from_raw_key(conn, raw_key)

    assert principal == APIKeyPrincipal(
        subject=f"api_key:{row['id']}",
        api_key_id=row["id"],
        name="Export client",
        key_prefix=row["key_prefix"],
        scopes=[EXPORT_READ_SCOPE],
        expires_at=None,
        created_by_user_id=str(row["created_by_user_id"]),
    )
    assert conn.api_keys_by_id[row["id"]]["last_used_at"] is not None
    assert "api_key" not in principal.model_dump()
    assert "key_hash" not in principal.model_dump()
    assert principal.key_prefix != raw_key


@pytest.mark.parametrize(
    "raw_key, expires_at, revoked, is_active",
    [
        ("missing", None, False, True),
        ("part3_expired", utc_now() - timedelta(minutes=1), False, True),
        ("part3_revoked", None, True, True),
        ("part3_inactive", None, False, False),
    ],
)
def test_resolve_current_api_key_rejects_invalid_expired_revoked_or_inactive_keys(
    raw_key: str,
    expires_at,
    revoked: bool,
    is_active: bool,
) -> None:
    conn = FakeAuthConnection()
    if raw_key != "missing":
        conn.add_api_key(raw_api_key=raw_key, scopes=[EXPORT_READ_SCOPE], expires_at=expires_at, revoked=revoked, is_active=is_active)

    with pytest.raises(HTTPException) as exc_info:
        resolve_current_api_key_from_raw_key(conn, raw_key)

    assert exc_info.value.status_code == 401


def test_scope_dependency_allows_required_scope_and_rejects_missing_scope() -> None:
    allowed = APIKeyPrincipal(
        subject="api_key:1",
        api_key_id="1",
        name="Export client",
        key_prefix="part3_valid",
        scopes=[EXPORT_READ_SCOPE],
        created_by_user_id="user-1",
    )
    denied = allowed.model_copy(update={"scopes": ["stats:read"]})

    assert require_api_key_scope(EXPORT_READ_SCOPE)(allowed) == allowed
    with pytest.raises(HTTPException) as exc_info:
        require_api_key_scope(EXPORT_READ_SCOPE)(denied)
    assert exc_info.value.status_code == 403
