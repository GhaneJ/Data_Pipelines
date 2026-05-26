"""CSV export service functions for application data."""

from __future__ import annotations

import csv
import io
from typing import Any

import psycopg

from backend.app.services.common import ApplicationFilters, build_application_filter_clause


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


def rows_to_csv(rows: list[dict[str, Any]]) -> str:
    """Serialize exported application rows to CSV text."""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=EXPORT_APPLICATION_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()
