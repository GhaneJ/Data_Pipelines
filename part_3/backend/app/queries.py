"""Raw SQL queries used by the FastAPI read endpoints."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import psycopg


APPLICATION_SELECT_SQL = """
SELECT
    a.diarienummer,
    a.source_year,
    a.source_file,
    a.source_sheet,
    a.source_row,
    a.utbildningsnamn,
    e.utbildningsomrade,
    a.beslut,
    a.decision_code AS beslut_normalized,
    a.is_approved,
    l.lan,
    l.kommun,
    a.flera_kommuner,
    a.has_multiple_municipalities,
    a.antal_kommuner,
    a.yh_poang,
    sf.studieform,
    a.is_distance_based,
    a.studietakt_procent,
    a.examenstyp,
    p.utbildningsanordnare,
    pt.huvudmannatyp,
    pt.huvudmannatyp_normalized,
    a.sokta_utbildningsomgangar,
    a.beviljade_utbildningsomgangar,
    a.sun5_inriktning,
    a.sun5_inriktning_namn,
    a.seqf_niva,
    a.smalt_yrkesomrade,
    a.sokta_platser_per_utbildningsomgang,
    a.sokta_platser_totalt,
    a.beviljade_platser_totalt
FROM applications a
JOIN education_areas e ON e.education_area_id = a.education_area_id
JOIN locations l ON l.location_id = a.location_id
JOIN providers p ON p.provider_id = a.provider_id
JOIN principal_types pt ON pt.principal_type_id = a.principal_type_id
JOIN study_forms sf ON sf.study_form_id = a.study_form_id
"""

APPLICATION_COUNT_SQL = """
SELECT COUNT(*) AS total
FROM applications a
JOIN education_areas e ON e.education_area_id = a.education_area_id
JOIN locations l ON l.location_id = a.location_id
JOIN providers p ON p.provider_id = a.provider_id
JOIN principal_types pt ON pt.principal_type_id = a.principal_type_id
JOIN study_forms sf ON sf.study_form_id = a.study_form_id
"""


@dataclass(frozen=True)
class ApplicationFilters:
    """Supported filters for the applications list endpoint."""

    source_year: int | None = None
    decision: str | None = None
    region: str | None = None
    municipality: str | None = None
    provider: str | None = None
    education_area: str | None = None
    study_form: str | None = None


def _like_pattern(value: str) -> str:
    """Prepare a case-insensitive partial-match pattern for PostgreSQL ILIKE."""
    return f"%{value.strip()}%"


def build_application_filter_clause(filters: ApplicationFilters) -> tuple[str, dict[str, Any]]:
    """Build the SQL WHERE clause and parameters for supported application filters."""
    clauses: list[str] = []
    params: dict[str, Any] = {}

    if filters.source_year is not None:
        clauses.append("a.source_year = %(source_year)s")
        params["source_year"] = filters.source_year

    if filters.decision:
        clauses.append("a.decision_code = %(decision)s")
        params["decision"] = filters.decision

    if filters.region:
        clauses.append("l.lan ILIKE %(region)s")
        params["region"] = _like_pattern(filters.region)

    if filters.municipality:
        clauses.append("l.kommun ILIKE %(municipality)s")
        params["municipality"] = _like_pattern(filters.municipality)

    if filters.provider:
        clauses.append("p.utbildningsanordnare ILIKE %(provider)s")
        params["provider"] = _like_pattern(filters.provider)

    if filters.education_area:
        clauses.append("e.utbildningsomrade ILIKE %(education_area)s")
        params["education_area"] = _like_pattern(filters.education_area)

    if filters.study_form:
        clauses.append("sf.studieform ILIKE %(study_form)s")
        params["study_form"] = _like_pattern(filters.study_form)

    if not clauses:
        return "", params

    return "WHERE " + " AND ".join(clauses), params


def fetch_applications(
    conn: psycopg.Connection[dict[str, Any]],
    filters: ApplicationFilters,
    limit: int,
    offset: int,
) -> dict[str, Any]:
    """Return one page of applications plus the total count for the same filters."""
    where_sql, params = build_application_filter_clause(filters)

    count_sql = f"{APPLICATION_COUNT_SQL}\n{where_sql};"
    data_sql = f"""
{APPLICATION_SELECT_SQL}
{where_sql}
ORDER BY a.source_year DESC, a.diarienummer
LIMIT %(limit)s OFFSET %(offset)s;
"""

    with conn.cursor() as cursor:
        cursor.execute(count_sql, params)
        total_row = cursor.fetchone()
        total = int(total_row["total"] if total_row else 0)

        cursor.execute(data_sql, {**params, "limit": limit, "offset": offset})
        items = cursor.fetchall()

    return {"total": total, "limit": limit, "offset": offset, "items": items}


def fetch_application_by_diarienummer(
    conn: psycopg.Connection[dict[str, Any]],
    diarienummer: str,
) -> dict[str, Any] | None:
    """Return one application by its natural identifier, or None if it is missing."""
    sql = f"""
{APPLICATION_SELECT_SQL}
WHERE a.diarienummer = %(diarienummer)s;
"""
    with conn.cursor() as cursor:
        cursor.execute(sql, {"diarienummer": diarienummer})
        return cursor.fetchone()
