"""Statistics and trend routes."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, status

from backend.app.dependencies import DatabaseConnection
from backend.app.schemas import (
    DecisionStats,
    DecisionTrend,
    EducationAreaStats,
    EducationAreaTrend,
    RegionStats,
    RegionTrend,
    YearStats,
)
from backend.app.services.common import TrendFilters, validate_year_range
from backend.app.services.stats import (
    fetch_stats_by_decision,
    fetch_stats_by_education_area,
    fetch_stats_by_region,
    fetch_stats_by_year,
    fetch_trend_by_decision,
    fetch_trend_by_education_area,
    fetch_trend_by_region,
)


router = APIRouter(tags=["statistics"])


def _check_year_range(year_from: int | None, year_to: int | None) -> None:
    """Translate service-level year range validation into an HTTP 400 response."""
    try:
        validate_year_range(year_from, year_to)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/stats/by-year", response_model=list[YearStats])
def get_stats_by_year(conn: DatabaseConnection) -> list[dict[str, Any]]:
    """Return application counts and approval rate grouped by source year."""
    return fetch_stats_by_year(conn)


@router.get("/stats/by-region", response_model=list[RegionStats])
def get_stats_by_region(conn: DatabaseConnection) -> list[dict[str, Any]]:
    """Return application counts and approval rate grouped by län/region."""
    return fetch_stats_by_region(conn)


@router.get("/stats/by-education-area", response_model=list[EducationAreaStats])
def get_stats_by_education_area(conn: DatabaseConnection) -> list[dict[str, Any]]:
    """Return application counts and approval rate grouped by education area."""
    return fetch_stats_by_education_area(conn)


@router.get("/stats/by-decision", response_model=list[DecisionStats])
def get_stats_by_decision(conn: DatabaseConnection) -> list[dict[str, Any]]:
    """Return application counts grouped by normalized decision."""
    return fetch_stats_by_decision(conn)


@router.get("/stats/trends/by-decision", response_model=list[DecisionTrend])
def get_trend_by_decision(
    conn: DatabaseConnection,
    year_from: Annotated[int | None, Query(ge=2020, le=2025)] = None,
    year_to: Annotated[int | None, Query(ge=2020, le=2025)] = None,
    decision: Annotated[str | None, Query(pattern="^(approved|rejected|withdrawn)$")] = None,
) -> list[dict[str, Any]]:
    """Return yearly trend rows grouped by normalized decision."""
    _check_year_range(year_from, year_to)
    filters = TrendFilters(year_from=year_from, year_to=year_to, decision=decision)
    return fetch_trend_by_decision(conn, filters)


@router.get("/stats/trends/by-region", response_model=list[RegionTrend])
def get_trend_by_region(
    conn: DatabaseConnection,
    year_from: Annotated[int | None, Query(ge=2020, le=2025)] = None,
    year_to: Annotated[int | None, Query(ge=2020, le=2025)] = None,
    region: Annotated[str | None, Query(description="Filter by län/region.")] = None,
    lan: Annotated[str | None, Query(description="Alias for region/län.")] = None,
    limit: Annotated[int | None, Query(ge=1, le=25, description="Return the top N regions across the selected years.")] = None,
) -> list[dict[str, Any]]:
    """Return yearly trend rows grouped by län/region."""
    _check_year_range(year_from, year_to)
    filters = TrendFilters(year_from=year_from, year_to=year_to, region=region or lan, limit=limit)
    return fetch_trend_by_region(conn, filters)


@router.get("/stats/trends/by-education-area", response_model=list[EducationAreaTrend])
def get_trend_by_education_area(
    conn: DatabaseConnection,
    year_from: Annotated[int | None, Query(ge=2020, le=2025)] = None,
    year_to: Annotated[int | None, Query(ge=2020, le=2025)] = None,
    education_area: Annotated[str | None, Query(description="Filter by utbildningsområde.")] = None,
    limit: Annotated[int | None, Query(ge=1, le=25, description="Return the top N education areas across the selected years.")] = None,
) -> list[dict[str, Any]]:
    """Return yearly trend rows grouped by education area."""
    _check_year_range(year_from, year_to)
    filters = TrendFilters(
        year_from=year_from,
        year_to=year_to,
        education_area=education_area,
        limit=limit,
    )
    return fetch_trend_by_education_area(conn, filters)
