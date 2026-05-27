"""Tests for explicit loader/reset separation."""

from __future__ import annotations

from backend.scripts import load_curated_data


def test_loader_defaults_separate_reset_schema_from_safe_schema() -> None:
    """Full reloads should use reset_schema.sql before safe schema.sql."""
    assert load_curated_data.DEFAULT_RESET_SCHEMA_PATH.name == "reset_schema.sql"
    assert load_curated_data.DEFAULT_SCHEMA_PATH.name == "schema.sql"
    assert load_curated_data.DEFAULT_INDEXES_PATH.name == "indexes.sql"


def test_reset_schema_preserves_local_admin_notes() -> None:
    """Curated-data reloads should not remove protected admin notes."""
    reset_sql = load_curated_data.read_sql(load_curated_data.DEFAULT_RESET_SCHEMA_PATH)

    assert "DROP TABLE IF EXISTS applications" in reset_sql
    assert "DROP TABLE IF EXISTS application_notes" not in reset_sql


def test_safe_schema_does_not_contain_reset_operations() -> None:
    """schema.sql is safe for API startup and should not reset data."""
    schema_sql = load_curated_data.read_sql(load_curated_data.DEFAULT_SCHEMA_PATH).upper()

    assert "DROP TABLE" not in schema_sql
    assert "TRUNCATE" not in schema_sql
    assert "DELETE FROM" not in schema_sql
