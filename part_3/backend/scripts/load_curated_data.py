"""Load the curated MYH applications CSV into PostgreSQL.

The curated CSV from Part 2 is the source of truth. This script keeps the load
process simple: create the schema, insert lookup rows, then insert one
application row per diarienummer.
"""

from __future__ import annotations

import argparse
import csv
import os
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import psycopg


REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA_PATH = BACKEND_ROOT / "sql" / "schema.sql"
DEFAULT_INDEXES_PATH = BACKEND_ROOT / "sql" / "indexes.sql"
DEFAULT_CSV_NAME = "myh_curated_applications_2020_2025.csv"
DEFAULT_CSV_CANDIDATES = (
    REPO_ROOT / "part_2" / "data" / "processed" / DEFAULT_CSV_NAME,
    REPO_ROOT / "part_3" / "data" / "processed" / DEFAULT_CSV_NAME,
    REPO_ROOT / DEFAULT_CSV_NAME,
    Path.cwd() / DEFAULT_CSV_NAME,
)

DECISION_LABELS = {
    "approved": "Approved",
    "rejected": "Rejected",
    "withdrawn": "Withdrawn",
}

REQUIRED_COLUMNS = {
    "source_year",
    "source_file",
    "source_sheet",
    "source_row",
    "diarienummer",
    "utbildningsnamn",
    "utbildningsomrade",
    "beslut",
    "beslut_normalized",
    "is_approved",
    "lan",
    "kommun",
    "flera_kommuner",
    "has_multiple_municipalities",
    "antal_kommuner",
    "yh_poang",
    "studieform",
    "is_distance_based",
    "studietakt_procent",
    "utbildningsanordnare",
    "huvudmannatyp",
    "huvudmannatyp_normalized",
    "sokta_utbildningsomgangar",
    "beviljade_utbildningsomgangar",
}

APPLICATION_INSERT_SQL = """
INSERT INTO applications (
    diarienummer,
    source_year,
    source_file,
    source_sheet,
    source_row,
    utbildningsnamn,
    education_area_id,
    decision_code,
    beslut,
    is_approved,
    location_id,
    provider_id,
    principal_type_id,
    study_form_id,
    flera_kommuner,
    has_multiple_municipalities,
    antal_kommuner,
    yh_poang,
    is_distance_based,
    studietakt_procent,
    examenstyp,
    sokta_utbildningsomgangar,
    beviljade_utbildningsomgangar,
    sun5_inriktning,
    sun5_inriktning_namn,
    seqf_niva,
    smalt_yrkesomrade,
    sokta_platser_per_utbildningsomgang,
    sokta_platser_totalt,
    beviljade_platser_totalt
)
VALUES (
    %(diarienummer)s,
    %(source_year)s,
    %(source_file)s,
    %(source_sheet)s,
    %(source_row)s,
    %(utbildningsnamn)s,
    %(education_area_id)s,
    %(decision_code)s,
    %(beslut)s,
    %(is_approved)s,
    %(location_id)s,
    %(provider_id)s,
    %(principal_type_id)s,
    %(study_form_id)s,
    %(flera_kommuner)s,
    %(has_multiple_municipalities)s,
    %(antal_kommuner)s,
    %(yh_poang)s,
    %(is_distance_based)s,
    %(studietakt_procent)s,
    %(examenstyp)s,
    %(sokta_utbildningsomgangar)s,
    %(beviljade_utbildningsomgangar)s,
    %(sun5_inriktning)s,
    %(sun5_inriktning_namn)s,
    %(seqf_niva)s,
    %(smalt_yrkesomrade)s,
    %(sokta_platser_per_utbildningsomgang)s,
    %(sokta_platser_totalt)s,
    %(beviljade_platser_totalt)s
);
"""


def parse_args() -> argparse.Namespace:
    """Read command-line arguments for the database load."""
    parser = argparse.ArgumentParser(description="Load curated MYH applications into PostgreSQL.")
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
    parser.add_argument(
        "--schema-path",
        type=Path,
        default=DEFAULT_SCHEMA_PATH,
        help="Path to schema.sql.",
    )
    parser.add_argument(
        "--indexes-path",
        type=Path,
        default=DEFAULT_INDEXES_PATH,
        help="Path to indexes.sql.",
    )
    parser.add_argument(
        "--skip-schema",
        action="store_true",
        help="Skip running schema.sql and indexes.sql before loading data.",
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


def read_rows(csv_path: Path) -> list[dict[str, str]]:
    """Read the curated CSV and verify that required columns exist."""
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    if not rows:
        raise ValueError("CSV file is empty.")

    actual_columns = set(rows[0].keys())
    missing_columns = sorted(REQUIRED_COLUMNS - actual_columns)
    if missing_columns:
        raise ValueError(f"CSV is missing required columns: {missing_columns}")

    return rows


def clean_text(value: str | None) -> str | None:
    """Normalize blank CSV text values to None."""
    if value is None:
        return None
    cleaned = value.strip()
    if cleaned == "" or cleaned.lower() == "nan":
        return None
    return cleaned


def require_text(row: dict[str, str], column: str) -> str:
    """Return a required text value or fail with a useful message."""
    value = clean_text(row.get(column))
    if value is None:
        raise ValueError(f"Required column {column!r} is empty for row: {row}")
    return value


def to_int(value: str | None, column: str) -> int:
    """Convert a required CSV number to int."""
    cleaned = clean_text(value)
    if cleaned is None:
        raise ValueError(f"Required integer column {column!r} is empty.")
    return int(Decimal(cleaned))


def to_optional_decimal(value: str | None) -> Decimal | None:
    """Convert an optional CSV number to Decimal."""
    cleaned = clean_text(value)
    if cleaned is None:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation as error:
        raise ValueError(f"Could not convert {value!r} to Decimal.") from error


def to_bool(value: str | None, column: str) -> bool:
    """Convert common CSV boolean strings to Python bool."""
    cleaned = clean_text(value)
    if cleaned is None:
        raise ValueError(f"Required boolean column {column!r} is empty.")

    normalized = cleaned.lower()
    if normalized in {"true", "1", "yes", "ja"}:
        return True
    if normalized in {"false", "0", "no", "nej"}:
        return False
    raise ValueError(f"Could not convert {value!r} to boolean for column {column!r}.")


def read_sql(path: Path) -> str:
    """Read a SQL file as UTF-8 text."""
    if not path.exists():
        raise FileNotFoundError(f"SQL file not found: {path}")
    return path.read_text(encoding="utf-8")


def run_sql_file(conn: psycopg.Connection[Any], path: Path) -> None:
    """Execute one project SQL file inside the current transaction."""
    with conn.cursor() as cursor:
        cursor.execute(read_sql(path))


def unique_values(rows: list[dict[str, str]], column: str) -> list[str]:
    """Return sorted unique non-empty values for a CSV column."""
    return sorted({require_text(row, column) for row in rows})


def insert_lookup_rows(conn: psycopg.Connection[Any], rows: list[dict[str, str]]) -> None:
    """Insert lookup/reference values before loading applications."""
    with conn.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO decisions (decision_code, decision_label)
            VALUES (%s, %s)
            ON CONFLICT (decision_code) DO NOTHING;
            """,
            [(code, DECISION_LABELS.get(code, code.title())) for code in unique_values(rows, "beslut_normalized")],
        )

        cursor.executemany(
            """
            INSERT INTO providers (utbildningsanordnare)
            VALUES (%s)
            ON CONFLICT (utbildningsanordnare) DO NOTHING;
            """,
            [(value,) for value in unique_values(rows, "utbildningsanordnare")],
        )

        cursor.executemany(
            """
            INSERT INTO education_areas (utbildningsomrade)
            VALUES (%s)
            ON CONFLICT (utbildningsomrade) DO NOTHING;
            """,
            [(value,) for value in unique_values(rows, "utbildningsomrade")],
        )

        # Location is a lookup because län + kommun will be common future API filters.
        locations = sorted({(require_text(row, "lan"), require_text(row, "kommun")) for row in rows})
        cursor.executemany(
            """
            INSERT INTO locations (lan, kommun)
            VALUES (%s, %s)
            ON CONFLICT (lan, kommun) DO NOTHING;
            """,
            locations,
        )

        principal_types = sorted(
            {
                (require_text(row, "huvudmannatyp"), require_text(row, "huvudmannatyp_normalized"))
                for row in rows
            }
        )
        cursor.executemany(
            """
            INSERT INTO principal_types (huvudmannatyp, huvudmannatyp_normalized)
            VALUES (%s, %s)
            ON CONFLICT (huvudmannatyp) DO NOTHING;
            """,
            principal_types,
        )

        cursor.executemany(
            """
            INSERT INTO study_forms (studieform)
            VALUES (%s)
            ON CONFLICT (studieform) DO NOTHING;
            """,
            [(value,) for value in unique_values(rows, "studieform")],
        )


def fetch_id_maps(conn: psycopg.Connection[Any]) -> dict[str, dict[Any, int]]:
    """Fetch lookup table IDs so CSV rows can reference them."""
    maps: dict[str, dict[Any, int]] = {}

    with conn.cursor() as cursor:
        cursor.execute("SELECT provider_id, utbildningsanordnare FROM providers;")
        maps["providers"] = {name: provider_id for provider_id, name in cursor.fetchall()}

        cursor.execute("SELECT education_area_id, utbildningsomrade FROM education_areas;")
        maps["education_areas"] = {name: area_id for area_id, name in cursor.fetchall()}

        cursor.execute("SELECT location_id, lan, kommun FROM locations;")
        maps["locations"] = {(lan, kommun): location_id for location_id, lan, kommun in cursor.fetchall()}

        cursor.execute("SELECT principal_type_id, huvudmannatyp FROM principal_types;")
        maps["principal_types"] = {name: type_id for type_id, name in cursor.fetchall()}

        cursor.execute("SELECT study_form_id, studieform FROM study_forms;")
        maps["study_forms"] = {name: form_id for form_id, name in cursor.fetchall()}

    return maps


def build_application_row(row: dict[str, str], id_maps: dict[str, dict[Any, int]]) -> dict[str, Any]:
    """Convert one CSV row into parameters for the applications insert."""
    lan = require_text(row, "lan")
    kommun = require_text(row, "kommun")
    provider = require_text(row, "utbildningsanordnare")
    education_area = require_text(row, "utbildningsomrade")
    principal_type = require_text(row, "huvudmannatyp")
    study_form = require_text(row, "studieform")

    return {
        "diarienummer": require_text(row, "diarienummer"),
        "source_year": to_int(row.get("source_year"), "source_year"),
        "source_file": require_text(row, "source_file"),
        "source_sheet": require_text(row, "source_sheet"),
        "source_row": to_int(row.get("source_row"), "source_row"),
        "utbildningsnamn": require_text(row, "utbildningsnamn"),
        "education_area_id": id_maps["education_areas"][education_area],
        "decision_code": require_text(row, "beslut_normalized"),
        "beslut": require_text(row, "beslut"),
        "is_approved": to_bool(row.get("is_approved"), "is_approved"),
        "location_id": id_maps["locations"][(lan, kommun)],
        "provider_id": id_maps["providers"][provider],
        "principal_type_id": id_maps["principal_types"][principal_type],
        "study_form_id": id_maps["study_forms"][study_form],
        "flera_kommuner": require_text(row, "flera_kommuner"),
        "has_multiple_municipalities": to_bool(
            row.get("has_multiple_municipalities"), "has_multiple_municipalities"
        ),
        "antal_kommuner": to_int(row.get("antal_kommuner"), "antal_kommuner"),
        "yh_poang": to_int(row.get("yh_poang"), "yh_poang"),
        "is_distance_based": to_bool(row.get("is_distance_based"), "is_distance_based"),
        "studietakt_procent": to_int(row.get("studietakt_procent"), "studietakt_procent"),
        "examenstyp": clean_text(row.get("examenstyp")),
        "sokta_utbildningsomgangar": to_int(
            row.get("sokta_utbildningsomgangar"), "sokta_utbildningsomgangar"
        ),
        "beviljade_utbildningsomgangar": to_int(
            row.get("beviljade_utbildningsomgangar"), "beviljade_utbildningsomgangar"
        ),
        "sun5_inriktning": clean_text(row.get("sun5_inriktning")),
        "sun5_inriktning_namn": clean_text(row.get("sun5_inriktning_namn")),
        "seqf_niva": to_optional_decimal(row.get("seqf_niva")),
        "smalt_yrkesomrade": clean_text(row.get("smalt_yrkesomrade")),
        "sokta_platser_per_utbildningsomgang": to_optional_decimal(
            row.get("sokta_platser_per_utbildningsomgang")
        ),
        "sokta_platser_totalt": to_optional_decimal(row.get("sokta_platser_totalt")),
        "beviljade_platser_totalt": to_optional_decimal(row.get("beviljade_platser_totalt")),
    }


def validate_source_rows(rows: list[dict[str, str]]) -> None:
    """Fail early if the CSV no longer matches the 3.2 schema assumptions."""
    diarienummer_values = [require_text(row, "diarienummer") for row in rows]
    if len(diarienummer_values) != len(set(diarienummer_values)):
        raise ValueError("diarienummer is not unique in the curated CSV.")

    years = {to_int(row.get("source_year"), "source_year") for row in rows}
    if min(years) != 2020 or max(years) != 2025:
        raise ValueError(f"Expected source_year range 2020-2025, found {sorted(years)}.")

    decisions = {require_text(row, "beslut_normalized") for row in rows}
    unexpected_decisions = decisions - set(DECISION_LABELS)
    if unexpected_decisions:
        raise ValueError(f"Unexpected normalized decision values: {sorted(unexpected_decisions)}")


def load_applications(conn: psycopg.Connection[Any], rows: list[dict[str, str]]) -> None:
    """Insert all application records after lookup tables exist."""
    id_maps = fetch_id_maps(conn)
    application_rows = [build_application_row(row, id_maps) for row in rows]

    with conn.cursor() as cursor:
        cursor.executemany(APPLICATION_INSERT_SQL, application_rows)



def format_source_path(csv_path: Path) -> str:
    """Return a readable source path for API and CLI summaries."""
    resolved = csv_path.resolve()
    for base_path in (REPO_ROOT, Path.cwd()):
        try:
            return resolved.relative_to(base_path.resolve()).as_posix()
        except ValueError:
            continue
    return resolved.as_posix()


def refresh_applications_database(
    csv_path: Path | None = None,
    database_url: str | None = None,
    schema_path: Path = DEFAULT_SCHEMA_PATH,
    indexes_path: Path = DEFAULT_INDEXES_PATH,
) -> dict[str, str | int]:
    """Reload PostgreSQL from the curated CSV and return a small summary."""
    database_url = database_url or os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("A PostgreSQL connection URL is required. Set DATABASE_URL before refreshing.")

    resolved_csv_path = resolve_csv_path(csv_path)
    rows = read_rows(resolved_csv_path)
    validate_source_rows(rows)

    with psycopg.connect(database_url) as conn:
        run_sql_file(conn, schema_path)
        run_sql_file(conn, indexes_path)
        insert_lookup_rows(conn, rows)
        load_applications(conn, rows)

    return {
        "status": "success",
        "rows_loaded": len(rows),
        "source_file": format_source_path(resolved_csv_path),
        "refreshed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }

def main() -> None:
    """Run schema creation, lookup loading, and application loading."""
    args = parse_args()
    if not args.database_url:
        raise ValueError("A PostgreSQL connection URL is required. Set DATABASE_URL or use --database-url.")

    if args.skip_schema:
        csv_path = resolve_csv_path(args.csv_path)
        rows = read_rows(csv_path)
        validate_source_rows(rows)

        with psycopg.connect(args.database_url) as conn:
            insert_lookup_rows(conn, rows)
            load_applications(conn, rows)

        print(f"Loaded {len(rows)} applications from {csv_path} into PostgreSQL.")
        return

    summary = refresh_applications_database(
        csv_path=args.csv_path,
        database_url=args.database_url,
        schema_path=args.schema_path,
        indexes_path=args.indexes_path,
    )
    print(
        f"Loaded {summary['rows_loaded']} applications from "
        f"{summary['source_file']} into PostgreSQL."
    )


if __name__ == "__main__":
    main()
