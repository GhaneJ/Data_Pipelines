"""Validate that PostgreSQL matches the curated MYH applications CSV.

Run this after load_curated_data.py. The checks confirm that PostgreSQL
preserves the curated dataset and is ready for the FastAPI backend.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path
from typing import Any

import psycopg


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CSV_NAME = "myh_curated_applications_2020_2025.csv"
DEFAULT_CSV_CANDIDATES = (
    REPO_ROOT / "part_2" / "data" / "processed" / DEFAULT_CSV_NAME,
    REPO_ROOT / "part_3" / "data" / "processed" / DEFAULT_CSV_NAME,
    REPO_ROOT / DEFAULT_CSV_NAME,
    Path.cwd() / DEFAULT_CSV_NAME,
)
EXPECTED_YEARS = {2020, 2021, 2022, 2023, 2024, 2025}
EXPECTED_DECISIONS = {"approved", "rejected", "withdrawn"}


class ValidationResult:
    """Collect validation failures while still printing every check."""

    def __init__(self) -> None:
        self.failed_checks: list[str] = []

    def check(self, name: str, condition: bool, details: str) -> None:
        """Print one PASS/FAIL line and remember failed checks."""
        status = "PASS" if condition else "FAIL"
        print(f"[{status}] {name}: {details}")
        if not condition:
            self.failed_checks.append(name)

    @property
    def ok(self) -> bool:
        """Return True when all recorded checks passed."""
        return not self.failed_checks


def parse_args() -> argparse.Namespace:
    """Read command-line arguments for validation."""
    parser = argparse.ArgumentParser(description="Validate the loaded MYH PostgreSQL database.")
    parser.add_argument(
        "--csv-path",
        type=Path,
        default=None,
        help="Path to myh_curated_applications_2020_2025.csv.",
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL"),
        help="PostgreSQL connection URL. Can also be supplied through DATABASE_URL.",
    )
    return parser.parse_args()


def resolve_csv_path(csv_path: Path | None) -> Path:
    """Return the explicit CSV path or the first known project location."""
    if csv_path is not None:
        return csv_path

    for candidate in DEFAULT_CSV_CANDIDATES:
        if candidate.exists():
            return candidate

    tried_paths = "\n".join(f"- {candidate}" for candidate in DEFAULT_CSV_CANDIDATES)
    raise FileNotFoundError(
        "Could not find the curated CSV automatically. "
        "Pass it explicitly with --csv-path. Tried:\n"
        f"{tried_paths}"
    )


def read_csv_rows(csv_path: Path) -> list[dict[str, str]]:
    """Read the curated CSV into dictionaries for comparison."""
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def fetch_scalar(conn: psycopg.Connection[Any], sql: str, params: tuple[Any, ...] = ()) -> Any:
    """Run a SQL query expected to return one value."""
    with conn.cursor() as cursor:
        cursor.execute(sql, params)
        row = cursor.fetchone()
    return row[0] if row else None


def fetch_set(conn: psycopg.Connection[Any], sql: str) -> set[Any]:
    """Run a SQL query and return the first column as a set."""
    with conn.cursor() as cursor:
        cursor.execute(sql)
        return {row[0] for row in cursor.fetchall()}


def validate_database(conn: psycopg.Connection[Any], rows: list[dict[str, str]]) -> ValidationResult:
    """Compare the loaded database with the curated CSV expectations."""
    result = ValidationResult()

    csv_count = len(rows)
    csv_ids = {row["diarienummer"].strip() for row in rows}
    csv_years = {int(row["source_year"]) for row in rows}
    csv_decisions = {row["beslut_normalized"].strip() for row in rows}

    db_count = fetch_scalar(conn, "SELECT COUNT(*) FROM applications;")
    result.check(
        "row count after load",
        db_count == csv_count,
        f"database={db_count}, csv={csv_count}",
    )

    distinct_ids = fetch_scalar(conn, "SELECT COUNT(DISTINCT diarienummer) FROM applications;")
    result.check(
        "unique diarienummer",
        distinct_ids == db_count,
        f"distinct={distinct_ids}, rows={db_count}",
    )

    min_year = fetch_scalar(conn, "SELECT MIN(source_year) FROM applications;")
    max_year = fetch_scalar(conn, "SELECT MAX(source_year) FROM applications;")
    db_years = fetch_set(conn, "SELECT DISTINCT source_year FROM applications;")
    result.check(
        "year range 2020-2025",
        min_year == 2020 and max_year == 2025 and db_years == EXPECTED_YEARS and csv_years == EXPECTED_YEARS,
        f"database_years={sorted(db_years)}, csv_years={sorted(csv_years)}",
    )

    db_decisions = fetch_set(conn, "SELECT DISTINCT decision_code FROM applications;")
    result.check(
        "expected normalized decision values",
        db_decisions == EXPECTED_DECISIONS and csv_decisions == EXPECTED_DECISIONS,
        f"database_decisions={sorted(db_decisions)}, csv_decisions={sorted(csv_decisions)}",
    )

    db_ids = fetch_set(conn, "SELECT diarienummer FROM applications;")
    missing_in_db = sorted(csv_ids - db_ids)
    unexpected_in_db = sorted(db_ids - csv_ids)
    result.check(
        "no unexpected loss of records",
        not missing_in_db and not unexpected_in_db,
        f"missing_in_db={len(missing_in_db)}, unexpected_in_db={len(unexpected_in_db)}",
    )

    # These joins are simple sanity checks that the lookup-table model is intact.
    fk_checks = {
        "decision foreign keys": """
            SELECT COUNT(*)
            FROM applications a
            LEFT JOIN decisions d ON d.decision_code = a.decision_code
            WHERE d.decision_code IS NULL;
        """,
        "provider foreign keys": """
            SELECT COUNT(*)
            FROM applications a
            LEFT JOIN providers p ON p.provider_id = a.provider_id
            WHERE p.provider_id IS NULL;
        """,
        "education area foreign keys": """
            SELECT COUNT(*)
            FROM applications a
            LEFT JOIN education_areas e ON e.education_area_id = a.education_area_id
            WHERE e.education_area_id IS NULL;
        """,
        "location foreign keys": """
            SELECT COUNT(*)
            FROM applications a
            LEFT JOIN locations l ON l.location_id = a.location_id
            WHERE l.location_id IS NULL;
        """,
        "principal type foreign keys": """
            SELECT COUNT(*)
            FROM applications a
            LEFT JOIN principal_types pt ON pt.principal_type_id = a.principal_type_id
            WHERE pt.principal_type_id IS NULL;
        """,
        "study form foreign keys": """
            SELECT COUNT(*)
            FROM applications a
            LEFT JOIN study_forms sf ON sf.study_form_id = a.study_form_id
            WHERE sf.study_form_id IS NULL;
        """,
    }

    for check_name, sql in fk_checks.items():
        broken_count = fetch_scalar(conn, sql)
        result.check(check_name, broken_count == 0, f"broken_references={broken_count}")

    return result


def print_year_summary(conn: psycopg.Connection[Any]) -> None:
    """Print a small row-count summary for manual review."""
    print("\nRows by source_year:")
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT source_year, COUNT(*)
            FROM applications
            GROUP BY source_year
            ORDER BY source_year;
            """
        )
        for source_year, row_count in cursor.fetchall():
            print(f"  {source_year}: {row_count}")


def main() -> None:
    """Run all validation checks and exit with a useful status code."""
    args = parse_args()
    if not args.database_url:
        raise ValueError("A PostgreSQL connection URL is required. Set DATABASE_URL or use --database-url.")

    csv_path = resolve_csv_path(args.csv_path)
    rows = read_csv_rows(csv_path)

    with psycopg.connect(args.database_url) as conn:
        result = validate_database(conn, rows)
        print_year_summary(conn)

    if result.ok:
        print("\nDatabase validation completed successfully.")
        sys.exit(0)

    print(f"\nDatabase validation failed: {', '.join(result.failed_checks)}")
    sys.exit(1)


if __name__ == "__main__":
    main()
