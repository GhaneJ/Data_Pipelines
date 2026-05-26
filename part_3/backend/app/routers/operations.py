"""Operational backend routes."""

from __future__ import annotations

import logging
from typing import Any

import psycopg
from fastapi import APIRouter, HTTPException, status

from backend.app.schemas import RefreshResult
from backend.scripts.load_curated_data import refresh_applications_database


logger = logging.getLogger(__name__)
router = APIRouter(tags=["operations"])


@router.post("/refresh", response_model=RefreshResult)
def refresh_applications() -> dict[str, Any]:
    """Reload PostgreSQL from the existing curated applications CSV."""
    try:
        return refresh_applications_database()
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
