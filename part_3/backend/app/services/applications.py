"""Application record browsing and lookup service functions."""

from __future__ import annotations

from typing import Any

import psycopg

from backend.app.services.common import (
    APPLICATION_COUNT_SQL,
    APPLICATION_SELECT_SQL,
    ApplicationFilters,
    build_application_filter_clause,
)


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
