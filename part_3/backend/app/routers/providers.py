"""Provider browsing routes."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, status

from backend.app.dependencies import DatabaseConnection
from backend.app.schemas import ApplicationList, ProviderList
from backend.app.services.providers import fetch_provider_applications, fetch_provider_by_id, fetch_providers


router = APIRouter(tags=["providers"])


@router.get("/providers", response_model=ProviderList)
def list_providers(
    conn: DatabaseConnection,
    q: Annotated[str | None, Query(description="Case-insensitive partial provider-name search.")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    """List providers with application counts and optional text search."""
    return fetch_providers(conn, search=q, limit=limit, offset=offset)


@router.get("/providers/{provider_id}/applications", response_model=ApplicationList)
def get_provider_applications(
    provider_id: int,
    conn: DatabaseConnection,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    """Return applications for one provider id."""
    provider = fetch_provider_by_id(conn, provider_id)
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider id {provider_id} was not found.",
        )
    return fetch_provider_applications(conn, provider_id=provider_id, limit=limit, offset=offset)
