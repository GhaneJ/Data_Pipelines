"""Tests for safe database seeder/bootstrap behavior."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

from backend.app.database import DatabaseConfigurationError
from backend.app.services import database_seeder


class RecordingCursor:
    """Cursor double that records SQL execution."""

    def __init__(self, connection: "RecordingConnection") -> None:
        self.connection = connection
        self._one: dict[str, object] | None = None
        self._all: list[dict[str, object]] = []

    def __enter__(self) -> "RecordingCursor":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    def execute(self, sql: str, params: object | None = None) -> None:
        self.connection.executed.append((sql, params))
        normalized_sql = " ".join(str(sql).lower().split())
        self._one = None
        self._all = []
        if "select 1 from pg_constraint" in normalized_sql:
            self._one = {"exists": 1}
        if "select conname" in normalized_sql and "from pg_constraint" in normalized_sql:
            self._all = []

    def executemany(self, sql: str, rows: object) -> None:
        self.connection.executed_many.append((sql, tuple(rows)))

    def fetchone(self) -> dict[str, object] | None:
        return self._one

    def fetchall(self) -> list[dict[str, object]]:
        return self._all


class RecordingConnection:
    """Connection double for seeder tests."""

    def __init__(self) -> None:
        self.executed: list[tuple[str, object | None]] = []
        self.executed_many: list[tuple[str, tuple[object, ...]]] = []

    def cursor(self) -> RecordingCursor:
        return RecordingCursor(self)


def test_project_managed_table_list_is_complete() -> None:
    """The seeder should know every project-managed table, including notes."""
    assert set(database_seeder.PROJECT_MANAGED_TABLES) == {
        "applications",
        "decisions",
        "education_areas",
        "locations",
        "principal_types",
        "providers",
        "study_forms",
        "application_notes",
        "auth_users",
        "auth_access_tokens",
        "api_keys",
        "provider_application_submissions",
        "provider_submission_review_events",
        "user_registration_requests",
        "auth_admin_events",
    }


def test_schema_sql_is_the_single_table_definition_source() -> None:
    """Safe schema.sql should contain every managed table definition."""
    schema_sql = database_seeder.read_sql_file(database_seeder.SCHEMA_PATH)

    for table_name in database_seeder.PROJECT_MANAGED_TABLES:
        assert f"CREATE TABLE IF NOT EXISTS {table_name}" in schema_sql


def test_indexes_sql_contains_required_indexes() -> None:
    """The startup seeder should include all expected indexes through indexes.sql."""
    indexes_sql = database_seeder.read_sql_file(database_seeder.INDEXES_PATH)

    for index_name in database_seeder.PROJECT_MANAGED_INDEXES:
        assert (
            f"CREATE INDEX IF NOT EXISTS {index_name}" in indexes_sql
            or f"CREATE UNIQUE INDEX IF NOT EXISTS {index_name}" in indexes_sql
        )


def test_startup_sql_files_are_non_destructive() -> None:
    """Startup SQL must not reset, truncate, or delete project data."""
    for sql_path in (database_seeder.SCHEMA_PATH, database_seeder.INDEXES_PATH):
        sql_text = database_seeder.read_sql_file(sql_path)
        database_seeder.assert_startup_sql_is_safe(sql_text, sql_path.name)


def test_reset_schema_is_explicit_and_preserves_application_notes() -> None:
    """The destructive reset file should be separated from safe startup SQL."""
    reset_sql = database_seeder.read_sql_file(database_seeder.SQL_ROOT / "reset_schema.sql")

    assert "DROP TABLE IF EXISTS applications" in reset_sql
    assert "DROP TABLE IF EXISTS application_notes" not in reset_sql


def test_startup_safety_rejects_destructive_sql(tmp_path: Path) -> None:
    """The seeder should fail clearly if unsafe SQL is accidentally wired in."""
    unsafe_sql = "CREATE TABLE IF NOT EXISTS demo (id int); DROP TABLE demo;"

    with pytest.raises(ValueError, match="Unsafe startup SQL"):
        database_seeder.assert_startup_sql_is_safe(unsafe_sql, "unsafe.sql")


def test_decision_seed_uses_safe_upsert() -> None:
    """Fixed decision rows should be seeded idempotently."""
    assert "ON CONFLICT" in database_seeder.SEED_CORE_DECISIONS_SQL
    assert database_seeder.CORE_DECISION_ROWS == (
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"),
    )


def test_ensure_database_ready_runs_schema_indexes_and_seed(monkeypatch: pytest.MonkeyPatch) -> None:
    """The public seeder entry point should orchestrate the safe startup flow."""
    conn = RecordingConnection()

    @contextmanager
    def fake_open_connection(database_url: str | None = None) -> Iterator[RecordingConnection]:
        yield conn

    monkeypatch.setattr(database_seeder, "open_connection", fake_open_connection)

    database_seeder.ensure_database_ready(database_url="postgresql://example/db")

    executed_sql = "\n".join(sql for sql, _ in conn.executed)
    assert "CREATE TABLE IF NOT EXISTS applications" in executed_sql
    assert "CREATE TABLE IF NOT EXISTS application_notes" in executed_sql
    assert "CREATE INDEX IF NOT EXISTS idx_application_notes_diarienummer" in executed_sql
    assert "CREATE TABLE IF NOT EXISTS api_keys" in executed_sql
    assert "CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash" in executed_sql
    assert "CREATE TABLE IF NOT EXISTS provider_application_submissions" in executed_sql
    assert "CREATE TABLE IF NOT EXISTS provider_submission_review_events" in executed_sql
    assert "ADD COLUMN IF NOT EXISTS review_started_at" in executed_sql
    assert "CREATE INDEX IF NOT EXISTS idx_provider_submissions_provider_id" in executed_sql
    assert "CREATE INDEX IF NOT EXISTS idx_provider_submission_review_events_submission_id" in executed_sql
    assert conn.executed_many
    assert conn.executed_many[0][1] == database_seeder.CORE_DECISION_ROWS


def test_missing_database_url_is_reported_clearly(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing DATABASE_URL should fail before any unclear connection behavior."""
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(DatabaseConfigurationError, match="DATABASE_URL is not set"):
        database_seeder.ensure_database_ready()


def test_auth_bootstrap_creates_admin_and_provider_users(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bootstrap env vars should create hashed local auth users idempotently."""
    from backend.tests.auth_test_utils import FakeAuthConnection

    conn = FakeAuthConnection()
    monkeypatch.setenv(database_seeder.BOOTSTRAP_ADMIN_USERNAME_ENV_VAR, "admin")
    monkeypatch.setenv(database_seeder.BOOTSTRAP_ADMIN_PASSWORD_ENV_VAR, "admin-password")
    monkeypatch.setenv(database_seeder.BOOTSTRAP_ADMIN_DISPLAY_NAME_ENV_VAR, "Local Admin")
    monkeypatch.setenv(database_seeder.BOOTSTRAP_PROVIDER_USERNAME_ENV_VAR, "provider")
    monkeypatch.setenv(database_seeder.BOOTSTRAP_PROVIDER_PASSWORD_ENV_VAR, "provider-password")
    monkeypatch.setenv(database_seeder.BOOTSTRAP_PROVIDER_DISPLAY_NAME_ENV_VAR, "Local Provider")
    monkeypatch.setenv(database_seeder.BOOTSTRAP_PROVIDER_ID_ENV_VAR, "999999")

    first = database_seeder.seed_auth_bootstrap_users(conn)
    second = database_seeder.seed_auth_bootstrap_users(conn)

    assert first == {"admin": "created", "provider": "created"}
    assert second == {"admin": "already_exists", "provider": "already_exists"}
    assert conn.users_by_username["admin"]["role"] == "admin"
    assert conn.users_by_username["admin"]["provider_id"] is None
    assert conn.users_by_username["provider"]["role"] == "provider"
    assert conn.users_by_username["provider"]["provider_id"] == "999999"
    assert conn.users_by_username["admin"]["password_hash"] != "admin-password"
    assert conn.users_by_username["provider"]["password_hash"] != "provider-password"


def test_provider_bootstrap_requires_provider_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provider bootstrap must not create an orphan provider user."""
    from backend.tests.auth_test_utils import FakeAuthConnection

    conn = FakeAuthConnection()
    monkeypatch.setenv(database_seeder.BOOTSTRAP_PROVIDER_USERNAME_ENV_VAR, "provider")
    monkeypatch.setenv(database_seeder.BOOTSTRAP_PROVIDER_PASSWORD_ENV_VAR, "provider-password")
    monkeypatch.setenv(database_seeder.BOOTSTRAP_PROVIDER_DISPLAY_NAME_ENV_VAR, "Local Provider")
    monkeypatch.delenv(database_seeder.BOOTSTRAP_PROVIDER_ID_ENV_VAR, raising=False)

    status = database_seeder.seed_auth_bootstrap_users(conn)

    assert status["provider"] == "provider_id_missing"
    assert "provider" not in conn.users_by_username


def test_auth_schema_can_be_added_without_resetting_curated_tables() -> None:
    """Safe startup schema should add auth tables without destructive reset SQL."""
    schema_sql = database_seeder.read_sql_file(database_seeder.SCHEMA_PATH)
    reset_sql = database_seeder.read_sql_file(database_seeder.SQL_ROOT / "reset_schema.sql")

    assert "CREATE TABLE IF NOT EXISTS auth_users" in schema_sql
    assert "CREATE TABLE IF NOT EXISTS auth_access_tokens" in schema_sql
    assert "DROP TABLE IF EXISTS auth_users" not in reset_sql
    assert "DROP TABLE IF EXISTS auth_access_tokens" not in reset_sql
    assert "DROP TABLE IF EXISTS api_keys" not in reset_sql
    assert "DROP TABLE IF EXISTS provider_application_submissions" not in reset_sql
    assert "DROP TABLE IF EXISTS provider_submission_review_events" not in reset_sql
