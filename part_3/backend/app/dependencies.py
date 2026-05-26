"""FastAPI dependency helpers shared by backend routers."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Annotated, Any

import psycopg
from fastapi import Depends, HTTPException, status

from backend.app.database import DatabaseConfigurationError, open_connection


logger = logging.getLogger(__name__)


def get_db_connection() -> Iterator[psycopg.Connection[dict[str, Any]]]:
    """Provide one PostgreSQL connection for one API request."""
    try:
        with open_connection() as conn:
            yield conn
    except DatabaseConfigurationError as exc:
        logger.error("Database configuration error: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    except psycopg.OperationalError as exc:
        logger.warning("Could not open database connection.", exc_info=exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not connect to the PostgreSQL database.",
        ) from exc


DatabaseConnection = Annotated[psycopg.Connection[dict[str, Any]], Depends(get_db_connection)]
