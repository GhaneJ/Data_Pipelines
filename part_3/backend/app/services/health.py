"""Database readiness checks used by the health endpoints."""

from __future__ import annotations

from typing import Any

import psycopg
from psycopg import sql


REQUIRED_TABLES = (
    "applications",
    "decisions",
    "providers",
    "education_areas",
    "locations",
    "principal_types",
    "study_forms",
    "application_notes",
    "auth_users",
    "auth_access_tokens",
)

LOOKUP_TABLES = (
    "decisions",
    "providers",
    "education_areas",
    "locations",
    "principal_types",
    "study_forms",
)


class DatabaseReadinessError(RuntimeError):
    """Raised when the database is reachable but not ready for the API."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        super().__init__(str(payload))


def fetch_public_table_names(conn: psycopg.Connection[dict[str, Any]]) -> set[str]:
    """Return all public table names visible in the current database."""
    query = """
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
    """
    with conn.cursor() as cursor:
        cursor.execute(query)
        return {row["table_name"] for row in cursor.fetchall()}


def fetch_table_count(conn: psycopg.Connection[dict[str, Any]], table_name: str) -> int:
    """Return a row count for an allowlisted readiness-check table."""
    if table_name not in REQUIRED_TABLES:
        raise ValueError(f"Unsupported readiness-check table: {table_name}")

    query = sql.SQL("SELECT COUNT(*)::integer AS row_count FROM {}").format(sql.Identifier(table_name))
    with conn.cursor() as cursor:
        cursor.execute(query)
        row = cursor.fetchone()
    return int(row["row_count"] if row else 0)


def build_not_ready_payload(
    required_tables: dict[str, Any],
    applications: dict[str, Any] | None = None,
    lookup_tables: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a consistent not-ready response payload."""
    return {
        "status": "not_ready",
        "database_connected": True,
        "required_tables": required_tables,
        "applications": applications,
        "lookup_tables": lookup_tables or [],
    }


def check_database_readiness(conn: psycopg.Connection[dict[str, Any]]) -> dict[str, Any]:
    """Check whether PostgreSQL has the tables and rows needed by the API."""
    existing_tables = fetch_public_table_names(conn)
    missing_tables = sorted(set(REQUIRED_TABLES) - existing_tables)
    required_tables = {
        "ok": not missing_tables,
        "checked": list(REQUIRED_TABLES),
        "missing": missing_tables,
    }

    if missing_tables:
        raise DatabaseReadinessError(build_not_ready_payload(required_tables=required_tables))

    applications_count = fetch_table_count(conn, "applications")
    applications = {
        "table": "applications",
        "ok": applications_count > 0,
        "row_count": applications_count,
    }

    lookup_results: list[dict[str, Any]] = []
    for table_name in LOOKUP_TABLES:
        row_count = fetch_table_count(conn, table_name)
        lookup_results.append(
            {
                "table": table_name,
                "ok": row_count > 0,
                "row_count": row_count,
            }
        )

    all_ready = applications["ok"] and all(table["ok"] for table in lookup_results)
    payload = {
        "status": "ready" if all_ready else "not_ready",
        "database_connected": True,
        "required_tables": required_tables,
        "applications": applications,
        "lookup_tables": lookup_results,
    }

    if not all_ready:
        raise DatabaseReadinessError(payload)

    return payload
