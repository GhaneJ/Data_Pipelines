"""Focused tests for database-backed role authorization helpers."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from backend.app.auth.dependencies import require_admin, require_provider
from backend.app.auth.models import AuthenticatedPrincipal, Role


def test_admin_dependency_accepts_database_backed_admin_principal() -> None:
    principal = AuthenticatedPrincipal(subject="user:1", username="admin", display_name="Local Admin", role=Role.ADMIN)

    assert require_admin(principal) == principal


def test_provider_dependency_accepts_database_backed_provider_principal() -> None:
    principal = AuthenticatedPrincipal(
        subject="user:2",
        username="provider",
        display_name="Local Provider",
        role=Role.PROVIDER,
        provider_id="999999",
    )

    assert require_provider(principal) == principal


def test_provider_is_forbidden_from_admin_dependency() -> None:
    principal = AuthenticatedPrincipal(
        subject="user:2",
        username="provider",
        display_name="Local Provider",
        role=Role.PROVIDER,
        provider_id="999999",
    )

    with pytest.raises(HTTPException) as exc_info:
        require_admin(principal)

    assert exc_info.value.status_code == 403
