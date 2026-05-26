"""Service and health-check routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status

from backend.app.dependencies import DatabaseConnection
from backend.app.schemas import DatabaseHealth, HealthStatus
from backend.app.services.health import DatabaseReadinessError, check_database_readiness


router = APIRouter(tags=["health"])


@router.get("/")
def read_root() -> dict[str, str]:
    """Return a small service description for manual browser checks."""
    return {
        "service": "MYH Applications API",
        "status": "ok",
        "docs": "/docs",
    }


@router.get("/health", response_model=HealthStatus)
def read_health() -> dict[str, str]:
    """Return a lightweight API health check response."""
    return {"status": "ok"}


@router.get("/health/db", response_model=DatabaseHealth)
def read_database_health(conn: DatabaseConnection) -> dict[str, Any]:
    """Return database readiness details for the API and future frontend."""
    try:
        return check_database_readiness(conn)
    except DatabaseReadinessError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=exc.payload) from exc
