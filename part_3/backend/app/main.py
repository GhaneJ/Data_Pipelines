"""FastAPI entry point for the MYH applications data service."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated, Any

import psycopg
from fastapi import Depends, FastAPI, HTTPException, Query, status

from backend.app.database import open_connection
from backend.app.queries import ApplicationFilters, fetch_application_by_diarienummer, fetch_applications
from backend.app.schemas import Application, ApplicationList


app = FastAPI(
    title="MYH Applications API",
    version="0.3.3",
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
