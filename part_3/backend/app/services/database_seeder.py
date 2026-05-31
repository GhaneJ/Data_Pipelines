"""Safe database bootstrap helpers for FastAPI startup.

The project uses SQL files as the schema source of truth. This service only
orchestrates safe startup behavior: connect to the existing PostgreSQL database,
run non-destructive schema/index SQL, seed fixed lookup rows, and optionally
create local database-backed bootstrap auth users.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any

import psycopg
from psycopg import sql

from backend.app.auth.models import Role
from backend.app.auth.password_hashing import hash_password
from backend.app.auth.repositories import create_bootstrap_user, find_user_by_username
from backend.app.database import open_connection


logger = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).resolve().parents[2]
SQL_ROOT = BACKEND_ROOT / "sql"
SCHEMA_PATH = SQL_ROOT / "schema.sql"
INDEXES_PATH = SQL_ROOT / "indexes.sql"

PROJECT_MANAGED_TABLES = (
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
    "myh_source_check_runs",
    "myh_source_files",
    "myh_refresh_runs",
    "admin_notifications",
)

PROJECT_MANAGED_INDEXES = (
    "idx_applications_source_year",
    "idx_applications_decision_code",
    "idx_applications_location_id",
    "idx_applications_provider_id",
    "idx_applications_education_area_id",
    "idx_applications_study_form_id",
    "idx_applications_principal_type_id",
    "idx_applications_year_decision",
    "idx_applications_distance_based",
    "idx_locations_lan_kommun",
    "idx_providers_name",
    "idx_education_areas_name",
    "idx_study_forms_name",
    "idx_application_notes_diarienummer",
    "idx_auth_users_username",
    "idx_auth_users_role",
    "idx_auth_users_provider_id",
    "idx_auth_access_tokens_token_hash",
    "idx_auth_access_tokens_user_id",
    "idx_auth_access_tokens_expires_at",
    "idx_api_keys_key_hash",
    "idx_api_keys_key_prefix",
    "idx_api_keys_is_active",
    "idx_api_keys_expires_at",
    "idx_api_keys_created_by_user_id",
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
    "idx_user_registration_requests_username",
    "idx_user_registration_requests_pending_username_unique",
    "idx_user_registration_requests_status",
    "idx_user_registration_requests_provider_id",
    "idx_user_registration_requests_created_at",
    "idx_auth_admin_events_actor_user_id",
    "idx_auth_admin_events_target_user_id",
    "idx_auth_admin_events_registration_request_id",
    "idx_auth_admin_events_action",
    "idx_auth_admin_events_created_at",
    "idx_myh_source_check_runs_started_at",
    "idx_myh_source_files_source_year",
    "idx_myh_source_files_status",
    "idx_myh_source_files_last_seen_at",
    "idx_myh_refresh_runs_source_file_id",
    "idx_myh_refresh_runs_started_at",
    "idx_myh_refresh_runs_status",
    "idx_admin_notifications_status",
    "idx_admin_notifications_created_at",
    "idx_admin_notifications_source_file_id",
    "idx_admin_notifications_refresh_run_id",
)

CORE_DECISION_ROWS = (
    ("approved", "Approved"),
    ("rejected", "Rejected"),
    ("withdrawn", "Withdrawn"),
)

BOOTSTRAP_ADMIN_USERNAME_ENV_VAR = "PART3_BOOTSTRAP_ADMIN_USERNAME"
BOOTSTRAP_ADMIN_PASSWORD_ENV_VAR = "PART3_BOOTSTRAP_ADMIN_PASSWORD"
BOOTSTRAP_ADMIN_DISPLAY_NAME_ENV_VAR = "PART3_BOOTSTRAP_ADMIN_DISPLAY_NAME"
BOOTSTRAP_PROVIDER_USERNAME_ENV_VAR = "PART3_BOOTSTRAP_PROVIDER_USERNAME"
BOOTSTRAP_PROVIDER_PASSWORD_ENV_VAR = "PART3_BOOTSTRAP_PROVIDER_PASSWORD"
BOOTSTRAP_PROVIDER_DISPLAY_NAME_ENV_VAR = "PART3_BOOTSTRAP_PROVIDER_DISPLAY_NAME"
BOOTSTRAP_PROVIDER_ID_ENV_VAR = "PART3_BOOTSTRAP_PROVIDER_ID"

DESTRUCTIVE_STARTUP_SQL_PATTERN = re.compile(r"\b(DROP|TRUNCATE)\b|\bDELETE\s+FROM\b", re.IGNORECASE)

SEED_CORE_DECISIONS_SQL = """
INSERT INTO decisions (decision_code, decision_label)
VALUES (%s, %s)
ON CONFLICT (decision_code) DO UPDATE
SET decision_label = EXCLUDED.decision_label;
"""


def strip_sql_comments(sql_text: str) -> str:
    """Remove SQL comments before checking startup safety."""
    without_block_comments = re.sub(r"/\*.*?\*/", "", sql_text, flags=re.DOTALL)
    lines = [line.split("--", 1)[0] for line in without_block_comments.splitlines()]
    return "\n".join(lines)


def assert_startup_sql_is_safe(sql_text: str, source_name: str) -> None:
    """Fail if startup SQL contains destructive operations."""
    uncommented_sql = strip_sql_comments(sql_text)
    match = DESTRUCTIVE_STARTUP_SQL_PATTERN.search(uncommented_sql)
    if match:
        operation = match.group(0).upper()
        raise ValueError(f"Unsafe startup SQL in {source_name}: {operation} is not allowed.")


def read_sql_file(path: Path) -> str:
    """Read a project SQL file or fail with a clear path-specific message."""
    if not path.exists():
        raise FileNotFoundError(f"SQL file not found: {path}")
    return path.read_text(encoding="utf-8")


def run_safe_sql_file(conn: psycopg.Connection[dict[str, Any]], path: Path) -> None:
    """Execute one startup-safe SQL file inside the current transaction."""
    sql_text = read_sql_file(path)
    assert_startup_sql_is_safe(sql_text, path.name)
    with conn.cursor() as cursor:
        cursor.execute(sql_text)


def seed_core_lookup_rows(conn: psycopg.Connection[dict[str, Any]]) -> None:
    """Seed tiny fixed lookup rows that do not depend on the curated CSV."""
    with conn.cursor() as cursor:
        cursor.executemany(SEED_CORE_DECISIONS_SQL, CORE_DECISION_ROWS)


def _constraint_exists(
    conn: psycopg.Connection[dict[str, Any]],
    *,
    table_name: str,
    constraint_name: str,
) -> bool:
    """Return whether a named project-managed constraint exists."""
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT 1
            FROM pg_constraint
            WHERE conrelid = %(table_name)s::regclass
              AND conname = %(constraint_name)s;
            """,
            {"table_name": table_name, "constraint_name": constraint_name},
        )
        return cursor.fetchone() is not None


def _drop_provider_submission_status_constraints(conn: psycopg.Connection[dict[str, Any]]) -> None:
    """Drop old 3.17 status checks before installing the 3.18 checks.

    This is code-managed schema upgrade logic, not a user-run manual ALTER. It
    only touches check constraints that reference provider-submission workflow
    status. Existing rows and curated data are preserved.
    """
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT conname, pg_get_constraintdef(oid) AS definition
            FROM pg_constraint
            WHERE conrelid = 'provider_application_submissions'::regclass
              AND contype = 'c';
            """
        )
        constraints = cursor.fetchall()

    for constraint in constraints:
        definition = str(constraint["definition"]).lower()
        if "status" not in definition:
            continue
        with conn.cursor() as cursor:
            cursor.execute(
                sql.SQL("ALTER TABLE provider_application_submissions DROP CONSTRAINT {}").format(
                    sql.Identifier(str(constraint["conname"]))
                )
            )


def ensure_provider_submission_review_schema(conn: psycopg.Connection[dict[str, Any]]) -> None:
    """Upgrade existing 3.17 provider-submission databases for 3.18.

    ``CREATE TABLE IF NOT EXISTS`` cannot update existing check constraints or
    add missing review metadata columns to already-created tables. This function
    performs the non-destructive, application-code-managed upgrade required for
    local databases that already contain 3.17 provider submissions.
    """
    with conn.cursor() as cursor:
        cursor.execute(
            """
            ALTER TABLE provider_application_submissions
                ADD COLUMN IF NOT EXISTS review_started_at TIMESTAMPTZ NULL,
                ADD COLUMN IF NOT EXISTS reviewed_by_user_id UUID NULL,
                ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ NULL,
                ADD COLUMN IF NOT EXISTS review_notes TEXT NULL;
            """
        )

    if not _constraint_exists(
        conn,
        table_name="provider_application_submissions",
        constraint_name="provider_submission_reviewed_by_user_id_fkey",
    ):
        with conn.cursor() as cursor:
            cursor.execute(
                """
                ALTER TABLE provider_application_submissions
                ADD CONSTRAINT provider_submission_reviewed_by_user_id_fkey
                FOREIGN KEY (reviewed_by_user_id) REFERENCES auth_users(id) ON DELETE SET NULL;
                """
            )

    if not (
        _constraint_exists(
            conn,
            table_name="provider_application_submissions",
            constraint_name="provider_submission_status_check",
        )
        and _constraint_exists(
            conn,
            table_name="provider_application_submissions",
            constraint_name="provider_submission_submitted_at_status_check",
        )
    ):
        _drop_provider_submission_status_constraints(conn)
        with conn.cursor() as cursor:
            cursor.execute(
                """
                ALTER TABLE provider_application_submissions
                ADD CONSTRAINT provider_submission_status_check
                CHECK (status IN ('draft', 'submitted', 'under_review', 'needs_changes', 'approved', 'rejected'));
                """
            )
            cursor.execute(
                """
                ALTER TABLE provider_application_submissions
                ADD CONSTRAINT provider_submission_submitted_at_status_check
                CHECK ((status = 'draft' AND submitted_at IS NULL) OR (status <> 'draft' AND submitted_at IS NOT NULL));
                """
            )


def ensure_applications_source_year_schema(conn: psycopg.Connection[dict[str, Any]]) -> None:
    """Upgrade existing applications source-year check for future official MYH files.

    Earlier project stages limited official historical data to 2020-2025. The
    3.20 source-monitoring refresh pipeline must be able to import newly
    published official MYH result years without a manual ALTER.
    """
    if not _constraint_exists(
        conn,
        table_name="applications",
        constraint_name="applications_source_year_check",
    ):
        return

    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT pg_get_constraintdef(oid) AS definition
            FROM pg_constraint
            WHERE conrelid = 'applications'::regclass
              AND conname = 'applications_source_year_check';
            """
        )
        row = cursor.fetchone()

    definition = str(row["definition"] if isinstance(row, dict) else row[0]) if row else ""
    if "2100" in definition:
        return

    with conn.cursor() as cursor:
        cursor.execute(
            """
            ALTER TABLE applications
            DROP CONSTRAINT applications_source_year_check;
            """
        )
        cursor.execute(
            """
            ALTER TABLE applications
            ADD CONSTRAINT applications_source_year_check
            CHECK (source_year BETWEEN 2020 AND 2100);
            """
        )


def _read_env(name: str) -> str | None:
    """Return a stripped environment variable value, or None when blank."""
    value = os.getenv(name, "").strip()
    return value or None


def _bootstrap_user_if_configured(
    conn: psycopg.Connection[dict[str, Any]],
    *,
    role: Role,
    username_env: str,
    password_env: str,
    display_name_env: str,
    provider_id_env: str | None = None,
) -> str:
    """Create one bootstrap user if all required variables are present.

    Returns a small status string used by tests and safe startup logs. Password
    values are never returned or logged.
    """
    username = _read_env(username_env)
    password = _read_env(password_env)
    display_name = _read_env(display_name_env)
    provider_id = _read_env(provider_id_env) if provider_id_env else None

    if not username and not password and not display_name and not provider_id:
        return "not_configured"
    if not username or not password or not display_name:
        return "incomplete"
    if role == Role.PROVIDER and not provider_id:
        return "provider_id_missing"

    existing_user = find_user_by_username(conn, username)
    if existing_user is not None:
        return "already_exists"

    create_bootstrap_user(
        conn,
        username=username,
        display_name=display_name,
        role=role,
        provider_id=provider_id,
        password_config=hash_password(password),
    )
    return "created"


def seed_auth_bootstrap_users(conn: psycopg.Connection[dict[str, Any]]) -> dict[str, str]:
    """Create local admin/provider auth users from bootstrap env vars.

    Bootstrap is safe and idempotent: existing users are not overwritten and raw
    bootstrap passwords are never stored or logged.
    """
    statuses = {
        "admin": _bootstrap_user_if_configured(
            conn,
            role=Role.ADMIN,
            username_env=BOOTSTRAP_ADMIN_USERNAME_ENV_VAR,
            password_env=BOOTSTRAP_ADMIN_PASSWORD_ENV_VAR,
            display_name_env=BOOTSTRAP_ADMIN_DISPLAY_NAME_ENV_VAR,
        ),
        "provider": _bootstrap_user_if_configured(
            conn,
            role=Role.PROVIDER,
            username_env=BOOTSTRAP_PROVIDER_USERNAME_ENV_VAR,
            password_env=BOOTSTRAP_PROVIDER_PASSWORD_ENV_VAR,
            display_name_env=BOOTSTRAP_PROVIDER_DISPLAY_NAME_ENV_VAR,
            provider_id_env=BOOTSTRAP_PROVIDER_ID_ENV_VAR,
        ),
    }

    for role, status in statuses.items():
        if status == "created":
            logger.info("Bootstrap %s user created.", role)
        elif status == "already_exists":
            logger.info("Bootstrap %s user already exists.", role)
        elif status in {"incomplete", "provider_id_missing"}:
            logger.warning("Bootstrap %s user not created because configuration is incomplete.", role)
    return statuses


def ensure_database_ready(
    database_url: str | None = None,
    schema_path: Path = SCHEMA_PATH,
    indexes_path: Path = INDEXES_PATH,
) -> None:
    """Ensure the existing PostgreSQL database has the project schema ready.

    The PostgreSQL database itself must already exist. This function never
    creates databases, drops tables, truncates data, deletes rows, or reloads
    curated CSV data.
    """
    with open_connection(database_url) as conn:
        run_safe_sql_file(conn, schema_path)
        ensure_provider_submission_review_schema(conn)
        ensure_applications_source_year_schema(conn)
        run_safe_sql_file(conn, indexes_path)
        seed_core_lookup_rows(conn)
        seed_auth_bootstrap_users(conn)
