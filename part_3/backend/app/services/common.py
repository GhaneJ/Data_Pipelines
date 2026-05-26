"""Shared SQL fragments and filter helpers for the MYH backend services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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
    """Supported filters for application browsing and CSV export."""

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


def like_pattern(value: str) -> str:
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
        params["region"] = like_pattern(filters.region)

    if filters.municipality:
        clauses.append("l.kommun ILIKE %(municipality)s")
        params["municipality"] = like_pattern(filters.municipality)

    if filters.provider:
        clauses.append("p.utbildningsanordnare ILIKE %(provider)s")
        params["provider"] = like_pattern(filters.provider)

    if filters.provider_id is not None:
        clauses.append("a.provider_id = %(provider_id)s")
        params["provider_id"] = filters.provider_id

    if filters.education_area:
        clauses.append("e.utbildningsomrade ILIKE %(education_area)s")
        params["education_area"] = like_pattern(filters.education_area)

    if filters.study_form:
        clauses.append("sf.studieform ILIKE %(study_form)s")
        params["study_form"] = like_pattern(filters.study_form)

    if not clauses:
        return "", params

    return "WHERE " + " AND ".join(clauses), params


def resolve_export_source_year(year: int | None, source_year: int | None) -> int | None:
    """Resolve the user-facing year filter and the source_year alias."""
    if year is not None and source_year is not None and year != source_year:
        raise ValueError("Use either year or source_year, or provide the same value for both.")
    return year if year is not None else source_year


def validate_year_range(year_from: int | None, year_to: int | None) -> None:
    """Reject trend year ranges where the start year is after the end year."""
    if year_from is not None and year_to is not None and year_from > year_to:
        raise ValueError("year_from must be less than or equal to year_to.")
