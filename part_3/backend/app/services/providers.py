"""Provider browsing service functions."""

from __future__ import annotations

from typing import Any

import psycopg

from backend.app.services.common import APPLICATION_SELECT_SQL, like_pattern


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


def build_provider_filter_clause(search: str | None) -> tuple[str, dict[str, Any]]:
    """Build a small WHERE clause for provider-name search."""
    if not search:
        return "", {}
    return "WHERE p.utbildningsanordnare ILIKE %(search)s", {"search": like_pattern(search)}


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
