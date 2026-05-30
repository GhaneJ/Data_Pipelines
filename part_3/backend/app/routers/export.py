"""CSV export routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response

from backend.app.api_keys.dependencies import require_api_key_scope
from backend.app.api_keys.models import APIKeyPrincipal, EXPORT_READ_SCOPE
from backend.app.dependencies import DatabaseConnection
from backend.app.services.common import ApplicationFilters, resolve_export_source_year
from backend.app.services.export import fetch_export_applications, rows_to_csv


router = APIRouter(tags=["export"])
ExportAPIKeyPrincipal = Annotated[APIKeyPrincipal, Depends(require_api_key_scope(EXPORT_READ_SCOPE))]


@router.get("/export/applications")
def export_applications_csv(
    conn: DatabaseConnection,
    api_key_principal: ExportAPIKeyPrincipal,
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
    """Export filtered applications as CSV using an export-scoped API key."""
    try:
        resolved_source_year = resolve_export_source_year(year=year, source_year=source_year)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    filters = ApplicationFilters(
        source_year=resolved_source_year,
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
