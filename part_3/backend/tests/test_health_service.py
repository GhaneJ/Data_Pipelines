"""Tests for database-readiness service behavior without PostgreSQL."""

from __future__ import annotations

import pytest

from backend.app.services import health as health_service


class DummyConnection:
    """Placeholder object used because these tests monkeypatch SQL access."""


def test_database_readiness_payload_when_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    """A complete database with rows should return a ready payload."""
    monkeypatch.setattr(
        health_service,
        "fetch_public_table_names",
        lambda conn: set(health_service.REQUIRED_TABLES),
    )
    monkeypatch.setattr(health_service, "fetch_table_count", lambda conn, table_name: 7641)

    payload = health_service.check_database_readiness(DummyConnection())

    assert payload["status"] == "ready"
    assert payload["database_connected"] is True
    assert payload["required_tables"]["missing"] == []
    assert payload["applications"]["row_count"] == 7641
    assert all(table["ok"] for table in payload["lookup_tables"])


def test_database_readiness_reports_missing_tables(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing required tables should become a clear not-ready payload."""
    monkeypatch.setattr(health_service, "fetch_public_table_names", lambda conn: {"applications"})

    with pytest.raises(health_service.DatabaseReadinessError) as exc_info:
        health_service.check_database_readiness(DummyConnection())

    payload = exc_info.value.payload
    assert payload["status"] == "not_ready"
    assert "providers" in payload["required_tables"]["missing"]
    assert payload["applications"] is None


def test_database_readiness_reports_empty_lookup_table(monkeypatch: pytest.MonkeyPatch) -> None:
    """An empty lookup table should make the database not ready."""
    monkeypatch.setattr(
        health_service,
        "fetch_public_table_names",
        lambda conn: set(health_service.REQUIRED_TABLES),
    )

    def fake_count(conn: object, table_name: str) -> int:
        return 0 if table_name == "providers" else 1

    monkeypatch.setattr(health_service, "fetch_table_count", fake_count)

    with pytest.raises(health_service.DatabaseReadinessError) as exc_info:
        health_service.check_database_readiness(DummyConnection())

    provider_check = next(table for table in exc_info.value.payload["lookup_tables"] if table["table"] == "providers")
    assert provider_check == {"table": "providers", "ok": False, "row_count": 0}
