"""Statistics and trend service functions for the MYH backend."""

from __future__ import annotations

from typing import Any

import psycopg

from backend.app.services.common import TrendFilters, like_pattern


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
        params["region"] = like_pattern(filters.region)

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
        params["education_area"] = like_pattern(filters.education_area)

    if not clauses:
        return "", params

    return "WHERE " + " AND ".join(clauses), params


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
