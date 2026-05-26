"""Central exception handlers for expected database-layer failures."""

from __future__ import annotations

import logging

import psycopg
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Register central handlers without hiding normal programming errors."""

    @app.exception_handler(psycopg.OperationalError)
    async def handle_database_unavailable(request: Request, exc: psycopg.OperationalError) -> JSONResponse:
        logger.warning("Database unavailable during %s %s", request.method, request.url.path, exc_info=exc)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "Could not connect to the PostgreSQL database."},
        )

    @app.exception_handler(psycopg.Error)
    async def handle_database_error(request: Request, exc: psycopg.Error) -> JSONResponse:
        logger.exception("Database error during %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "A database operation failed. Check the backend logs for details."},
        )
