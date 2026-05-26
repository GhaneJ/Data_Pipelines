"""Application browsing and record-access routes."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, status

from backend.app.dependencies import DatabaseConnection
from backend.app.schemas import Application, ApplicationList
from backend.app.services.applications import fetch_application_by_diarienummer, fetch_applications
from backend.app.services.common import ApplicationFilters


router = APIRouter(tags=["applications"])


@router.get("/applications", response_model=ApplicationList)
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


@router.get("/applications/{diarienummer:path}", response_model=Application)
def get_application(diarienummer: str, conn: DatabaseConnection) -> dict[str, Any]:
    """Return one application by diarienummer."""
    application = fetch_application_by_diarienummer(conn, diarienummer)
    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application {diarienummer!r} was not found.",
        )
    return application
