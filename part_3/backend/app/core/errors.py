"""Helpers for safe, consistent API error responses."""

from __future__ import annotations

from typing import Any

from fastapi import status
from fastapi.responses import JSONResponse
from starlette.requests import Request

from backend.app.middleware.request_context import REQUEST_ID_HEADER, get_request_id


GENERIC_INTERNAL_ERROR_MESSAGE = "An internal server error occurred."
VALIDATION_ERROR_MESSAGE = "Request validation failed."


def error_code_for_status(status_code: int) -> str:
    """Map common HTTP statuses to stable API error codes."""
    if status_code == status.HTTP_400_BAD_REQUEST:
        return "bad_request"
    if status_code == status.HTTP_401_UNAUTHORIZED:
        return "unauthorized"
    if status_code == status.HTTP_403_FORBIDDEN:
        return "forbidden"
    if status_code == status.HTTP_404_NOT_FOUND:
        return "not_found"
    if status_code == status.HTTP_409_CONFLICT:
        return "conflict"
    if status_code == 422:
        return "validation_error"
    if status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
        return "service_unavailable"
    if status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
        return "internal_server_error"
    return "http_error"


def message_from_http_detail(status_code: int, detail: Any) -> str:
    """Return a safe message for an HTTPException detail value."""
    if status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
        return GENERIC_INTERNAL_ERROR_MESSAGE

    if isinstance(detail, str) and detail.strip():
        return detail

    if status_code == 422:
        return VALIDATION_ERROR_MESSAGE
    return "The request could not be completed."


def build_error_payload(
    *,
    code: str,
    message: str,
    request_id: str,
    detail: Any | None = None,
    extra_error_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the standard error envelope.

    A top-level ``detail`` field is kept for backward compatibility with the
    existing dashboard/API helpers, while the new ``error`` envelope is the
    stable shape for new backend tests and future auth/API-key clients.
    """
    error: dict[str, Any] = {
        "code": code,
        "message": message,
        "request_id": request_id,
    }
    if extra_error_fields:
        error.update(extra_error_fields)

    payload: dict[str, Any] = {"error": error}
    payload["detail"] = detail if detail is not None else message
    return payload


def build_error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    detail: Any | None = None,
    extra_error_fields: dict[str, Any] | None = None,
) -> JSONResponse:
    """Return a JSON error response with request id in body and headers."""
    request_id = get_request_id(request)
    return JSONResponse(
        status_code=status_code,
        content=build_error_payload(
            code=code,
            message=message,
            request_id=request_id,
            detail=detail,
            extra_error_fields=extra_error_fields,
        ),
        headers={REQUEST_ID_HEADER: request_id},
    )
