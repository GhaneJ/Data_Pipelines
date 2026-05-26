"""Operational backend routes."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import psycopg
from fastapi import APIRouter, HTTPException, Query, status

from backend.app.schemas import RefreshResult, SourceCheckResult
from backend.app.services.source_check import (
    build_refresh_source_metadata,
    read_source_status_manifest,
    run_source_check,
)
from backend.scripts.load_curated_data import refresh_applications_database


logger = logging.getLogger(__name__)
router = APIRouter(tags=["operations"])


def _parse_checked_at(value: str | None) -> datetime | None:
    """Parse a manifest timestamp if it is present and valid."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _validate_recent_source_check(manifest: dict[str, Any], max_age_hours: int) -> None:
    """Reject refresh when the caller explicitly requires a recent successful source check."""
    if manifest.get("status") == "not_checked":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No recorded source check exists. Run POST /operations/check-source first.",
        )

    if manifest.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The latest source check failed. Review /operations/source-status before refreshing.",
        )

    checked_at = _parse_checked_at(manifest.get("checked_at"))
    if checked_at is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The latest source-check manifest has no valid checked_at timestamp.",
        )

    max_age = timedelta(hours=max_age_hours)
    now = datetime.now(timezone.utc)
    if now - checked_at > max_age:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The latest source check is older than {max_age_hours} hour(s). Run POST /operations/check-source first.",
        )


@router.get("/operations/source-status", response_model=SourceCheckResult)
def get_source_status() -> dict[str, Any]:
    """Return the latest local MYH source-check manifest without calling the internet."""
    return read_source_status_manifest()


@router.post("/operations/check-source", response_model=SourceCheckResult)
def check_source() -> dict[str, Any]:
    """Check the configured MYH source page and update the local status manifest."""
    return run_source_check(write_manifest=True)


@router.post("/refresh", response_model=RefreshResult)
def refresh_applications(
    require_recent_source_check: bool = Query(
        False,
        description="Require a recent successful source-check manifest before reloading from the curated CSV.",
    ),
    max_source_check_age_hours: int = Query(
        24,
        ge=1,
        le=168,
        description="Maximum source-check age accepted when require_recent_source_check is true.",
    ),
) -> dict[str, Any]:
    """Reload PostgreSQL from the existing curated applications CSV."""
    manifest = read_source_status_manifest()
    if require_recent_source_check:
        _validate_recent_source_check(manifest, max_source_check_age_hours)

    source_check_metadata = build_refresh_source_metadata(manifest)

    try:
        return refresh_applications_database(source_check_metadata=source_check_metadata)
    except FileNotFoundError as exc:
        logger.warning("Refresh failed because the curated CSV was not found: %s", exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ValueError as exc:
        logger.warning("Refresh rejected invalid input or state: %s", exc)
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR if "connection URL" in str(exc) else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    except psycopg.OperationalError as exc:
        logger.warning("Refresh could not connect to PostgreSQL.", exc_info=exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not connect to the PostgreSQL database during refresh.",
        ) from exc
    except psycopg.Error as exc:
        logger.exception("Refresh failed while loading the curated CSV.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database refresh failed while loading the curated CSV.",
        ) from exc
