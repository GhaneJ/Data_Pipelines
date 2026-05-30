"""Schema/startup tests for provider application submissions."""

from __future__ import annotations

from backend.app.services import database_seeder


def test_provider_submission_table_is_project_managed() -> None:
    schema_sql = database_seeder.read_sql_file(database_seeder.SCHEMA_PATH)

    assert "provider_application_submissions" in database_seeder.PROJECT_MANAGED_TABLES
    assert "CREATE TABLE IF NOT EXISTS provider_application_submissions" in schema_sql
    assert "provider_id TEXT NOT NULL" in schema_sql
    assert "created_by_user_id UUID NOT NULL REFERENCES auth_users" in schema_sql
    assert "CHECK (status IN ('draft', 'submitted'))" in schema_sql
    assert "CHECK ((status = 'submitted' AND submitted_at IS NOT NULL) OR (status = 'draft' AND submitted_at IS NULL))" in schema_sql


def test_provider_submission_indexes_are_project_managed() -> None:
    indexes_sql = database_seeder.read_sql_file(database_seeder.INDEXES_PATH)

    for index_name in {
        "idx_provider_submissions_provider_id",
        "idx_provider_submissions_created_by_user_id",
        "idx_provider_submissions_status",
        "idx_provider_submissions_target_year",
        "idx_provider_submissions_created_at",
    }:
        assert index_name in database_seeder.PROJECT_MANAGED_INDEXES
        assert f"CREATE INDEX IF NOT EXISTS {index_name}" in indexes_sql


def test_provider_submission_schema_is_startup_safe_and_non_destructive() -> None:
    schema_sql = database_seeder.read_sql_file(database_seeder.SCHEMA_PATH)
    indexes_sql = database_seeder.read_sql_file(database_seeder.INDEXES_PATH)
    reset_sql = database_seeder.read_sql_file(database_seeder.SQL_ROOT / "reset_schema.sql")

    database_seeder.assert_startup_sql_is_safe(schema_sql, "schema.sql")
    database_seeder.assert_startup_sql_is_safe(indexes_sql, "indexes.sql")
    assert "CREATE TABLE IF NOT EXISTS provider_application_submissions" in schema_sql
    assert "CREATE INDEX IF NOT EXISTS idx_provider_submissions_provider_id" in indexes_sql
    assert "DROP TABLE IF EXISTS provider_application_submissions" not in reset_sql
    assert "DROP TABLE IF EXISTS applications" in reset_sql
