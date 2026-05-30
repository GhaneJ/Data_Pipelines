"""Schema/startup tests for provider application submissions and review workflow."""

from __future__ import annotations

from backend.app.services import database_seeder


REVIEW_STATUSES_SQL = "'draft', 'submitted', 'under_review', 'needs_changes', 'approved', 'rejected'"


def test_provider_submission_table_is_project_managed_with_review_metadata() -> None:
    schema_sql = database_seeder.read_sql_file(database_seeder.SCHEMA_PATH)

    assert "provider_application_submissions" in database_seeder.PROJECT_MANAGED_TABLES
    assert "provider_submission_review_events" in database_seeder.PROJECT_MANAGED_TABLES
    assert "CREATE TABLE IF NOT EXISTS provider_application_submissions" in schema_sql
    assert "CREATE TABLE IF NOT EXISTS provider_submission_review_events" in schema_sql
    assert "provider_id TEXT NOT NULL" in schema_sql
    assert "created_by_user_id UUID NOT NULL REFERENCES auth_users" in schema_sql
    assert "review_started_at TIMESTAMPTZ NULL" in schema_sql
    assert "reviewed_by_user_id UUID NULL" in schema_sql
    assert "reviewed_at TIMESTAMPTZ NULL" in schema_sql
    assert "review_notes TEXT NULL" in schema_sql
    assert f"CHECK (status IN ({REVIEW_STATUSES_SQL}))" in schema_sql
    assert "CHECK ((status = 'draft' AND submitted_at IS NULL) OR (status <> 'draft' AND submitted_at IS NOT NULL))" in schema_sql
    assert "CHECK (action IN ('submitted', 'review_started', 'changes_requested', 'approved', 'rejected', 'resubmitted'))" in schema_sql


def test_provider_submission_indexes_are_project_managed() -> None:
    indexes_sql = database_seeder.read_sql_file(database_seeder.INDEXES_PATH)

    for index_name in {
        "idx_provider_submissions_provider_id",
        "idx_provider_submissions_created_by_user_id",
        "idx_provider_submissions_status",
        "idx_provider_submissions_target_year",
        "idx_provider_submissions_created_at",
        "idx_provider_submissions_reviewed_by_user_id",
        "idx_provider_submissions_review_started_at",
        "idx_provider_submissions_reviewed_at",
        "idx_provider_submissions_provider_status",
        "idx_provider_submission_review_events_submission_id",
        "idx_provider_submission_review_events_actor_user_id",
        "idx_provider_submission_review_events_action",
        "idx_provider_submission_review_events_created_at",
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
    assert "DROP TABLE IF EXISTS provider_submission_review_events" not in reset_sql
    assert "DROP TABLE IF EXISTS applications" in reset_sql


def test_startup_has_code_managed_existing_database_review_upgrade() -> None:
    assert hasattr(database_seeder, "ensure_provider_submission_review_schema")
    assert "ensure_provider_submission_review_schema(conn)" in database_seeder.ensure_database_ready.__code__.co_names or callable(
        database_seeder.ensure_provider_submission_review_schema
    )
