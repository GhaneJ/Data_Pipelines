"""Central exception handlers for safe API error responses."""

from __future__ import annotations

import logging

import psycopg
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.core.errors import (
    GENERIC_INTERNAL_ERROR_MESSAGE,
    VALIDATION_ERROR_MESSAGE,
    build_error_response,
    error_code_for_status,
    message_from_http_detail,
)
from backend.app.middleware.request_context import get_request_id


logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Register central handlers for expected and unexpected API errors."""

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = error_code_for_status(exc.status_code)
        message = message_from_http_detail(exc.status_code, exc.detail)
        detail = message if exc.status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR else exc.detail
        logger.info(
            "HTTP error request_id=%s method=%s path=%s status_code=%s code=%s",
            get_request_id(request),
            request.method,
            request.url.path,
            exc.status_code,
            code,
        )
        return build_error_response(
            request,
            status_code=exc.status_code,
            code=code,
            message=message,
            detail=detail,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        logger.info(
            "Validation error request_id=%s method=%s path=%s errors=%s",
            get_request_id(request),
            request.method,
            request.url.path,
            len(exc.errors()),
        )
        return build_error_response(
            request,
            status_code=422,
            code="validation_error",
            message=VALIDATION_ERROR_MESSAGE,
            detail=VALIDATION_ERROR_MESSAGE,
            extra_error_fields={"invalid_params": exc.errors()},
        )

    @app.exception_handler(psycopg.OperationalError)
    async def handle_database_unavailable(request: Request, exc: psycopg.OperationalError) -> JSONResponse:
        logger.warning(
            "Database unavailable request_id=%s method=%s path=%s",
            get_request_id(request),
            request.method,
            request.url.path,
            exc_info=True,
        )
        message = "Could not connect to the PostgreSQL database."
        return build_error_response(
            request,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="database_unavailable",
            message=message,
            detail=message,
        )

    @app.exception_handler(psycopg.Error)
    async def handle_database_error(request: Request, exc: psycopg.Error) -> JSONResponse:
        logger.exception(
            "Database error request_id=%s method=%s path=%s",
            get_request_id(request),
            request.method,
            request.url.path,
        )
        message = "A database operation failed. Check the backend logs for details."
        return build_error_response(
            request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="database_error",
            message=message,
            detail=message,
        )

    @app.exception_handler(Exception)
    async def handle_unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "Unhandled API error request_id=%s method=%s path=%s",
            get_request_id(request),
            request.method,
            request.url.path,
        )
        return build_error_response(
            request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="internal_server_error",
            message=GENERIC_INTERNAL_ERROR_MESSAGE,
            detail=GENERIC_INTERNAL_ERROR_MESSAGE,
        )
