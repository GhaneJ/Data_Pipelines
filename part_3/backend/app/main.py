"""FastAPI entry point for the MYH applications data service."""

from __future__ import annotations

import csv
import io
from collections.abc import Iterator
from typing import Annotated, Any

import psycopg
from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.responses import Response

from backend.app.database import open_connection
from backend.app.queries import (
    EXPORT_APPLICATION_COLUMNS,
    ApplicationFilters,
    TrendFilters,
    fetch_application_by_diarienummer,
    fetch_applications,
    fetch_export_applications,
    fetch_provider_applications,
    fetch_provider_by_id,
    fetch_providers,
    fetch_stats_by_decision,
    fetch_stats_by_education_area,
    fetch_stats_by_region,
    fetch_stats_by_year,
    fetch_trend_by_decision,
    fetch_trend_by_education_area,
    fetch_trend_by_region,
)
from backend.app.schemas import (
    Application,
    ApplicationList,
    DecisionStats,
    DecisionTrend,
    EducationAreaStats,
    EducationAreaTrend,
    ProviderList,
    RegionStats,
    RegionTrend,
    YearStats,
)


app = FastAPI(
    title="MYH Applications API",
    version="0.3.6",
    description="Read API for the curated MYH applications dataset stored in PostgreSQL.",
)


def get_db_connection() -> Iterator[psycopg.Connection[dict[str, Any]]]:
    """Provide one PostgreSQL connection for a request."""
    try:
        with open_connection() as conn:
            yield conn
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    except psycopg.OperationalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not connect to the PostgreSQL database.",
        ) from exc


DatabaseConnection = Annotated[psycopg.Connection[dict[str, Any]], Depends(get_db_connection)]


def resolve_export_source_year(year: int | None, source_year: int | None) -> int | None:
    """Resolve the user-facing year filter and the source_year alias."""
    if year is not None and source_year is not None and year != source_year:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use either year or source_year, or provide the same value for both.",
        )
    return year if year is not None else source_year


def validate_year_range(year_from: int | None, year_to: int | None) -> None:
    """Reject trend year ranges where the start year is after the end year."""
    if year_from is not None and year_to is not None and year_from > year_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="year_from must be less than or equal to year_to.",
        )


def rows_to_csv(rows: list[dict[str, Any]]) -> str:
    """Serialize exported application rows to CSV text."""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=EXPORT_APPLICATION_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


@app.get("/")
def read_root() -> dict[str, str]:
    """Return a small service description for manual browser checks."""
    return {
        "service": "MYH Applications API",
        "status": "ok",
        "docs": "/docs",
    }


@app.get("/health")
def read_health() -> dict[str, str]:
    """Return a simple health check response."""
    return {"status": "ok"}


@app.get("/applications", response_model=ApplicationList)
def list_applications(
    conn: DatabaseConnection,
    source_year: Annotated[int | None, Query(ge=2020, le=2025)] = None,
    decision: Annotated[str | None, Query(pattern="^(approved|rejected|withdrawn)$")] = None,
    region: Annotated[str | None, Query(description="Filter by län/region.")] = None,
    lan: Annotated[str | None, Query(description="Alias for region/län.")] = None,
    municipality: Annotated[str | None, Query(description="Filter by kommun/municipality.")] = None,
    kommun: Annotated[str | None, Query(description="Alias for municipality/kommun.")] = None,
    provider: Annotated[str | None, Query(description="Filter by utbildningsanordnare.")] = None,
    education_area: Annotated[str | None, Query(description="Filter by utbildningsområde.")] = None,
    study_form: Annotated[str | None, Query(description="Filter by studieform.")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    """List application records with useful filters and pagination."""
    filters = ApplicationFilters(
        source_year=source_year,
        decision=decision,
        region=region or lan,
        municipality=municipality or kommun,
        provider=provider,
        education_area=education_area,
        study_form=study_form,
    )
    return fetch_applications(conn, filters, limit=limit, offset=offset)


@app.get("/applications/{diarienummer:path}", response_model=Application)
def get_application(diarienummer: str, conn: DatabaseConnection) -> dict[str, Any]:
    """Return one application by diarienummer."""
    application = fetch_application_by_diarienummer(conn, diarienummer)
    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application {diarienummer!r} was not found.",
        )
    return application


@app.get("/export/applications")
def export_applications_csv(
    conn: DatabaseConnection,
    year: Annotated[int | None, Query(ge=2020, le=2025, description="User-facing alias for source_year.")] = None,
    source_year: Annotated[int | None, Query(ge=2020, le=2025, description="Source-year alias for export filters.")] = None,
    decision: Annotated[str | None, Query(pattern="^(approved|rejected|withdrawn)$")] = None,
    region: Annotated[str | None, Query(description="Filter by län/region.")] = None,
    lan: Annotated[str | None, Query(description="Alias for region/län.")] = None,
    municipality: Annotated[str | None, Query(description="Filter by kommun/municipality.")] = None,
    kommun: Annotated[str | None, Query(description="Alias for municipality/kommun.")] = None,
    provider: Annotated[str | None, Query(description="Partial provider-name filter.")] = None,
    provider_id: Annotated[int | None, Query(ge=1, description="Exact numeric provider id filter.")] = None,
    education_area: Annotated[str | None, Query(description="Filter by utbildningsområde.")] = None,
    study_form: Annotated[str | None, Query(description="Filter by studieform.")] = None,
    limit: Annotated[int | None, Query(ge=1, le=10000, description="Optional row limit for testing or smaller exports.")] = None,
) -> Response:
    """Export filtered applications as a downloadable CSV file."""
    filters = ApplicationFilters(
        source_year=resolve_export_source_year(year=year, source_year=source_year),
        decision=decision,
        region=region or lan,
        municipality=municipality or kommun,
        provider=provider,
        provider_id=provider_id,
        education_area=education_area,
        study_form=study_form,
    )
    rows = fetch_export_applications(conn, filters=filters, limit=limit)
    csv_text = rows_to_csv(rows)
    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="myh_applications_export.csv"'},
    )


@app.get("/stats/by-year", response_model=list[YearStats])
def get_stats_by_year(conn: DatabaseConnection) -> list[dict[str, Any]]:
    """Return application counts and approval rate grouped by source year."""
    return fetch_stats_by_year(conn)


@app.get("/stats/by-region", response_model=list[RegionStats])
def get_stats_by_region(conn: DatabaseConnection) -> list[dict[str, Any]]:
    """Return application counts and approval rate grouped by län/region."""
    return fetch_stats_by_region(conn)


@app.get("/stats/by-education-area", response_model=list[EducationAreaStats])
def get_stats_by_education_area(conn: DatabaseConnection) -> list[dict[str, Any]]:
    """Return application counts and approval rate grouped by education area."""
    return fetch_stats_by_education_area(conn)


@app.get("/stats/by-decision", response_model=list[DecisionStats])
def get_stats_by_decision(conn: DatabaseConnection) -> list[dict[str, Any]]:
    """Return application counts grouped by normalized decision."""
    return fetch_stats_by_decision(conn)


@app.get("/stats/trends/by-decision", response_model=list[DecisionTrend])
def get_trend_by_decision(
    conn: DatabaseConnection,
    year_from: Annotated[int | None, Query(ge=2020, le=2025)] = None,
    year_to: Annotated[int | None, Query(ge=2020, le=2025)] = None,
    decision: Annotated[str | None, Query(pattern="^(approved|rejected|withdrawn)$")] = None,
) -> list[dict[str, Any]]:
    """Return yearly application counts grouped by normalized decision."""
    validate_year_range(year_from, year_to)
    filters = TrendFilters(year_from=year_from, year_to=year_to, decision=decision)
    return fetch_trend_by_decision(conn, filters)


@app.get("/stats/trends/by-region", response_model=list[RegionTrend])
def get_trend_by_region(
    conn: DatabaseConnection,
    year_from: Annotated[int | None, Query(ge=2020, le=2025)] = None,
    year_to: Annotated[int | None, Query(ge=2020, le=2025)] = None,
    region: Annotated[str | None, Query(description="Optional län/region filter.")] = None,
    lan: Annotated[str | None, Query(description="Alias for region/län.")] = None,
    limit: Annotated[int | None, Query(ge=1, le=50, description="Optional number of top regions to include.")] = None,
) -> list[dict[str, Any]]:
    """Return yearly application counts grouped by län/region."""
    validate_year_range(year_from, year_to)
    filters = TrendFilters(year_from=year_from, year_to=year_to, region=region or lan, limit=limit)
    return fetch_trend_by_region(conn, filters)


@app.get("/stats/trends/by-education-area", response_model=list[EducationAreaTrend])
def get_trend_by_education_area(
    conn: DatabaseConnection,
    year_from: Annotated[int | None, Query(ge=2020, le=2025)] = None,
    year_to: Annotated[int | None, Query(ge=2020, le=2025)] = None,
    education_area: Annotated[str | None, Query(description="Optional education-area filter.")] = None,
    limit: Annotated[int | None, Query(ge=1, le=50, description="Optional number of top education areas to include.")] = None,
) -> list[dict[str, Any]]:
    """Return yearly application counts grouped by education area."""
    validate_year_range(year_from, year_to)
    filters = TrendFilters(
        year_from=year_from,
        year_to=year_to,
        education_area=education_area,
        limit=limit,
    )
    return fetch_trend_by_education_area(conn, filters)


@app.get("/providers", response_model=ProviderList)
def list_providers(
    conn: DatabaseConnection,
    q: Annotated[str | None, Query(description="Optional partial provider-name search.")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    """List providers with application counts and simple name search."""
    return fetch_providers(conn, search=q, limit=limit, offset=offset)


@app.get("/providers/{provider_id}/applications", response_model=ApplicationList)
def list_provider_applications(
    provider_id: int,
    conn: DatabaseConnection,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    """List applications for one provider id."""
    provider = fetch_provider_by_id(conn, provider_id)
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider id {provider_id!r} was not found.",
        )
    return fetch_provider_applications(conn, provider_id=provider_id, limit=limit, offset=offset)
