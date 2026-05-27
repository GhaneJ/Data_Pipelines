"""Safe database bootstrap helpers for FastAPI startup.

The project uses SQL files as the schema source of truth. This service only
orchestrates safe startup behavior: connect to the existing PostgreSQL database,
run non-destructive schema/index SQL, and seed fixed lookup rows.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import psycopg

from backend.app.database import open_connection


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
)

CORE_DECISION_ROWS = (
    ("approved", "Approved"),
    ("rejected", "Rejected"),
    ("withdrawn", "Withdrawn"),
)

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
        run_safe_sql_file(conn, indexes_path)
        seed_core_lookup_rows(conn)
