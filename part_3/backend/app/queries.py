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

EXPORT_APPLICATION_COLUMNS = [
    "diarienummer",
    "source_year",
    "utbildningsnamn",
    "utbildningsomrade",
    "beslut",
    "beslut_normalized",
    "is_approved",
    "lan",
    "kommun",
    "yh_poang",
    "studieform",
    "studietakt_procent",
    "utbildningsanordnare",
    "huvudmannatyp",
    "huvudmannatyp_normalized",
    "sokta_utbildningsomgangar",
    "beviljade_utbildningsomgangar",
    "sokta_platser_totalt",
    "beviljade_platser_totalt",
]

EXPORT_APPLICATION_SELECT_SQL = """
SELECT
    a.diarienummer,
    a.source_year,
    a.utbildningsnamn,
    e.utbildningsomrade,
    a.beslut,
    a.decision_code AS beslut_normalized,
    a.is_approved,
    l.lan,
    l.kommun,
    a.yh_poang,
    sf.studieform,
    a.studietakt_procent,
    p.utbildningsanordnare,
    pt.huvudmannatyp,
    pt.huvudmannatyp_normalized,
    a.sokta_utbildningsomgangar,
    a.beviljade_utbildningsomgangar,
    a.sokta_platser_totalt,
    a.beviljade_platser_totalt
FROM applications a
JOIN education_areas e ON e.education_area_id = a.education_area_id
JOIN locations l ON l.location_id = a.location_id
JOIN providers p ON p.provider_id = a.provider_id
JOIN principal_types pt ON pt.principal_type_id = a.principal_type_id
JOIN study_forms sf ON sf.study_form_id = a.study_form_id
"""

PROVIDER_SUMMARY_SELECT_SQL = """
SELECT
    p.provider_id,
    p.utbildningsanordnare,
    COUNT(a.diarienummer)::integer AS total_applications,
    SUM(CASE WHEN a.decision_code = 'approved' THEN 1 ELSE 0 END)::integer AS approved_applications,
    MIN(a.source_year)::integer AS first_year,
    MAX(a.source_year)::integer AS last_year
FROM providers p
LEFT JOIN applications a ON a.provider_id = p.provider_id
"""


@dataclass(frozen=True)
class ApplicationFilters:
    """Supported filters for the applications list endpoint."""

    source_year: int | None = None
    decision: str | None = None
    region: str | None = None
    municipality: str | None = None
    provider: str | None = None
    provider_id: int | None = None
    education_area: str | None = None
    study_form: str | None = None


@dataclass(frozen=True)
class TrendFilters:
    """Supported filters for yearly trend endpoints."""

    year_from: int | None = None
    year_to: int | None = None
    decision: str | None = None
    region: str | None = None
    education_area: str | None = None
    limit: int | None = None


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

    if filters.provider_id is not None:
        clauses.append("a.provider_id = %(provider_id)s")
        params["provider_id"] = filters.provider_id

    if filters.education_area:
        clauses.append("e.utbildningsomrade ILIKE %(education_area)s")
        params["education_area"] = _like_pattern(filters.education_area)

    if filters.study_form:
        clauses.append("sf.studieform ILIKE %(study_form)s")
        params["study_form"] = _like_pattern(filters.study_form)

    if not clauses:
        return "", params

    return "WHERE " + " AND ".join(clauses), params


def _add_trend_year_clauses(
    filters: TrendFilters,
    clauses: list[str],
    params: dict[str, Any],
) -> None:
    """Add the shared source_year range filters used by trend queries."""
    if filters.year_from is not None:
        clauses.append("a.source_year >= %(year_from)s")
        params["year_from"] = filters.year_from

    if filters.year_to is not None:
        clauses.append("a.source_year <= %(year_to)s")
        params["year_to"] = filters.year_to


def build_decision_trend_filter_clause(filters: TrendFilters) -> tuple[str, dict[str, Any]]:
    """Build filters for yearly decision trends."""
    clauses: list[str] = []
    params: dict[str, Any] = {}
    _add_trend_year_clauses(filters, clauses, params)

    if filters.decision:
        clauses.append("a.decision_code = %(decision)s")
        params["decision"] = filters.decision

    if not clauses:
        return "", params

    return "WHERE " + " AND ".join(clauses), params


def build_region_trend_filter_clause(filters: TrendFilters) -> tuple[str, dict[str, Any]]:
    """Build filters for yearly region trends."""
    clauses: list[str] = []
    params: dict[str, Any] = {}
    _add_trend_year_clauses(filters, clauses, params)

    if filters.region:
        clauses.append("l.lan ILIKE %(region)s")
        params["region"] = _like_pattern(filters.region)

    if not clauses:
        return "", params

    return "WHERE " + " AND ".join(clauses), params


def build_education_area_trend_filter_clause(filters: TrendFilters) -> tuple[str, dict[str, Any]]:
    """Build filters for yearly education-area trends."""
    clauses: list[str] = []
    params: dict[str, Any] = {}
    _add_trend_year_clauses(filters, clauses, params)

    if filters.education_area:
        clauses.append("e.utbildningsomrade ILIKE %(education_area)s")
        params["education_area"] = _like_pattern(filters.education_area)

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


def fetch_export_applications(
    conn: psycopg.Connection[dict[str, Any]],
    filters: ApplicationFilters,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Return filtered application rows for CSV export."""
    where_sql, params = build_application_filter_clause(filters)
    limit_sql = ""
    if limit is not None:
        limit_sql = "LIMIT %(limit)s"
        params = {**params, "limit": limit}

    sql = f"""
{EXPORT_APPLICATION_SELECT_SQL}
{where_sql}
ORDER BY a.source_year DESC, a.diarienummer
{limit_sql};
"""
    with conn.cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchall()


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


def fetch_stats_by_year(conn: psycopg.Connection[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return simple yearly application statistics from PostgreSQL."""
    sql = """
    SELECT
        a.source_year,
        COUNT(*)::integer AS total_applications,
        SUM(CASE WHEN a.decision_code = 'approved' THEN 1 ELSE 0 END)::integer AS approved_applications,
        SUM(CASE WHEN a.decision_code = 'rejected' THEN 1 ELSE 0 END)::integer AS rejected_applications,
        SUM(CASE WHEN a.decision_code = 'withdrawn' THEN 1 ELSE 0 END)::integer AS withdrawn_applications,
        ROUND(
            SUM(CASE WHEN a.decision_code = 'approved' THEN 1 ELSE 0 END) * 100.0 / COUNT(*),
            1
        )::float AS approval_rate_percent
    FROM applications a
    GROUP BY a.source_year
    ORDER BY a.source_year;
    """
    with conn.cursor() as cursor:
        cursor.execute(sql)
        return cursor.fetchall()


def fetch_stats_by_region(conn: psycopg.Connection[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return application statistics grouped by Swedish län/region."""
    sql = """
    SELECT
        l.lan,
        COUNT(*)::integer AS total_applications,
        SUM(CASE WHEN a.decision_code = 'approved' THEN 1 ELSE 0 END)::integer AS approved_applications,
        SUM(CASE WHEN a.decision_code = 'rejected' THEN 1 ELSE 0 END)::integer AS rejected_applications,
        SUM(CASE WHEN a.decision_code = 'withdrawn' THEN 1 ELSE 0 END)::integer AS withdrawn_applications,
        ROUND(
            SUM(CASE WHEN a.decision_code = 'approved' THEN 1 ELSE 0 END) * 100.0 / COUNT(*),
            1
        )::float AS approval_rate_percent
    FROM applications a
    JOIN locations l ON l.location_id = a.location_id
    GROUP BY l.lan
    ORDER BY total_applications DESC, l.lan;
    """
    with conn.cursor() as cursor:
        cursor.execute(sql)
        return cursor.fetchall()


def fetch_stats_by_education_area(conn: psycopg.Connection[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return application statistics grouped by education area."""
    sql = """
    SELECT
        e.education_area_id,
        e.utbildningsomrade,
        COUNT(*)::integer AS total_applications,
        SUM(CASE WHEN a.decision_code = 'approved' THEN 1 ELSE 0 END)::integer AS approved_applications,
        SUM(CASE WHEN a.decision_code = 'rejected' THEN 1 ELSE 0 END)::integer AS rejected_applications,
        SUM(CASE WHEN a.decision_code = 'withdrawn' THEN 1 ELSE 0 END)::integer AS withdrawn_applications,
        ROUND(
            SUM(CASE WHEN a.decision_code = 'approved' THEN 1 ELSE 0 END) * 100.0 / COUNT(*),
            1
        )::float AS approval_rate_percent
    FROM applications a
    JOIN education_areas e ON e.education_area_id = a.education_area_id
    GROUP BY e.education_area_id, e.utbildningsomrade
    ORDER BY total_applications DESC, e.utbildningsomrade;
    """
    with conn.cursor() as cursor:
        cursor.execute(sql)
        return cursor.fetchall()


def fetch_stats_by_decision(conn: psycopg.Connection[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return application counts grouped by normalized decision."""
    sql = """
    SELECT
        d.decision_code,
        d.decision_label,
        COUNT(a.diarienummer)::integer AS total_applications,
        ROUND(
            COUNT(a.diarienummer) * 100.0 / NULLIF((SELECT COUNT(*) FROM applications), 0),
            1
        )::float AS application_share_percent
    FROM decisions d
    LEFT JOIN applications a ON a.decision_code = d.decision_code
    GROUP BY d.decision_code, d.decision_label
    ORDER BY total_applications DESC, d.decision_code;
    """
    with conn.cursor() as cursor:
        cursor.execute(sql)
        return cursor.fetchall()


def fetch_trend_by_decision(
    conn: psycopg.Connection[dict[str, Any]],
    filters: TrendFilters,
) -> list[dict[str, Any]]:
    """Return yearly application counts grouped by normalized decision."""
    where_sql, params = build_decision_trend_filter_clause(filters)
    sql = f"""
    SELECT
        a.source_year,
        d.decision_code,
        d.decision_label,
        COUNT(*)::integer AS application_count
    FROM applications a
    JOIN decisions d ON d.decision_code = a.decision_code
    {where_sql}
    GROUP BY a.source_year, d.decision_code, d.decision_label
    ORDER BY a.source_year, d.decision_code;
    """
    with conn.cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchall()


def fetch_trend_by_region(
    conn: psycopg.Connection[dict[str, Any]],
    filters: TrendFilters,
) -> list[dict[str, Any]]:
    """Return yearly application counts grouped by län/region."""
    where_sql, params = build_region_trend_filter_clause(filters)

    if filters.limit is not None:
        params = {**params, "limit": filters.limit}
        sql = f"""
        WITH top_regions AS (
            SELECT
                l.lan
            FROM applications a
            JOIN locations l ON l.location_id = a.location_id
            {where_sql}
            GROUP BY l.lan
            ORDER BY COUNT(*) DESC, l.lan
            LIMIT %(limit)s
        )
        SELECT
            a.source_year,
            l.lan,
            COUNT(*)::integer AS application_count
        FROM applications a
        JOIN locations l ON l.location_id = a.location_id
        JOIN top_regions tr ON tr.lan = l.lan
        {where_sql}
        GROUP BY a.source_year, l.lan
        ORDER BY a.source_year, application_count DESC, l.lan;
        """
    else:
        sql = f"""
        SELECT
            a.source_year,
            l.lan,
            COUNT(*)::integer AS application_count
        FROM applications a
        JOIN locations l ON l.location_id = a.location_id
        {where_sql}
        GROUP BY a.source_year, l.lan
        ORDER BY a.source_year, application_count DESC, l.lan;
        """

    with conn.cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchall()


def fetch_trend_by_education_area(
    conn: psycopg.Connection[dict[str, Any]],
    filters: TrendFilters,
) -> list[dict[str, Any]]:
    """Return yearly application counts grouped by education area."""
    where_sql, params = build_education_area_trend_filter_clause(filters)

    if filters.limit is not None:
        params = {**params, "limit": filters.limit}
        sql = f"""
        WITH top_education_areas AS (
            SELECT
                e.education_area_id
            FROM applications a
            JOIN education_areas e ON e.education_area_id = a.education_area_id
            {where_sql}
            GROUP BY e.education_area_id, e.utbildningsomrade
            ORDER BY COUNT(*) DESC, e.utbildningsomrade
            LIMIT %(limit)s
        )
        SELECT
            a.source_year,
            e.education_area_id,
            e.utbildningsomrade,
            COUNT(*)::integer AS application_count
        FROM applications a
        JOIN education_areas e ON e.education_area_id = a.education_area_id
        JOIN top_education_areas tea ON tea.education_area_id = e.education_area_id
        {where_sql}
        GROUP BY a.source_year, e.education_area_id, e.utbildningsomrade
        ORDER BY a.source_year, application_count DESC, e.utbildningsomrade;
        """
    else:
        sql = f"""
        SELECT
            a.source_year,
            e.education_area_id,
            e.utbildningsomrade,
            COUNT(*)::integer AS application_count
        FROM applications a
        JOIN education_areas e ON e.education_area_id = a.education_area_id
        {where_sql}
        GROUP BY a.source_year, e.education_area_id, e.utbildningsomrade
        ORDER BY a.source_year, application_count DESC, e.utbildningsomrade;
        """

    with conn.cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchall()


def build_provider_filter_clause(search: str | None) -> tuple[str, dict[str, Any]]:
    """Build a small WHERE clause for provider name search."""
    if not search:
        return "", {}
    return "WHERE p.utbildningsanordnare ILIKE %(search)s", {"search": _like_pattern(search)}


def fetch_providers(
    conn: psycopg.Connection[dict[str, Any]],
    search: str | None,
    limit: int,
    offset: int,
) -> dict[str, Any]:
    """Return one page of providers with basic application counts."""
    where_sql, params = build_provider_filter_clause(search)
    count_sql = f"SELECT COUNT(*) AS total FROM providers p {where_sql};"
    data_sql = f"""
{PROVIDER_SUMMARY_SELECT_SQL}
{where_sql}
GROUP BY p.provider_id, p.utbildningsanordnare
ORDER BY total_applications DESC, p.utbildningsanordnare
LIMIT %(limit)s OFFSET %(offset)s;
"""

    with conn.cursor() as cursor:
        cursor.execute(count_sql, params)
        total_row = cursor.fetchone()
        total = int(total_row["total"] if total_row else 0)

        cursor.execute(data_sql, {**params, "limit": limit, "offset": offset})
        items = cursor.fetchall()

    return {"total": total, "limit": limit, "offset": offset, "items": items}


def fetch_provider_by_id(
    conn: psycopg.Connection[dict[str, Any]],
    provider_id: int,
) -> dict[str, Any] | None:
    """Return provider summary information for one provider id."""
    sql = f"""
{PROVIDER_SUMMARY_SELECT_SQL}
WHERE p.provider_id = %(provider_id)s
GROUP BY p.provider_id, p.utbildningsanordnare;
"""
    with conn.cursor() as cursor:
        cursor.execute(sql, {"provider_id": provider_id})
        return cursor.fetchone()


def fetch_provider_applications(
    conn: psycopg.Connection[dict[str, Any]],
    provider_id: int,
    limit: int,
    offset: int,
) -> dict[str, Any]:
    """Return one page of applications for one provider id."""
    count_sql = "SELECT COUNT(*) AS total FROM applications a WHERE a.provider_id = %(provider_id)s;"
    data_sql = f"""
{APPLICATION_SELECT_SQL}
WHERE a.provider_id = %(provider_id)s
ORDER BY a.source_year DESC, a.diarienummer
LIMIT %(limit)s OFFSET %(offset)s;
"""
    params = {"provider_id": provider_id}

    with conn.cursor() as cursor:
        cursor.execute(count_sql, params)
        total_row = cursor.fetchone()
        total = int(total_row["total"] if total_row else 0)

        cursor.execute(data_sql, {**params, "limit": limit, "offset": offset})
        items = cursor.fetchall()

    return {"total": total, "limit": limit, "offset": offset, "items": items}
