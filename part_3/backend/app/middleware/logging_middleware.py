"""Safe HTTP request logging middleware."""

from __future__ import annotations

import logging
from time import perf_counter
from urllib.parse import parse_qsl, urlencode

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.app.middleware.request_context import get_request_id


logger = logging.getLogger("backend.app.request")

_SENSITIVE_QUERY_PARTS = ("token", "authorization", "api_key", "apikey", "password", "secret", "key")
_MAX_QUERY_VALUE_LENGTH = 80


def _is_sensitive_query_key(key: str) -> bool:
    """Return True when a query parameter name may contain credentials."""
    lowered = key.lower().replace("-", "_")
    return any(part in lowered for part in _SENSITIVE_QUERY_PARTS)


def build_safe_query_string(query: str) -> str:
    """Return a log-safe query string with credential-like values redacted."""
    if not query:
        return ""

    safe_items: list[tuple[str, str]] = []
    for key, value in parse_qsl(query, keep_blank_values=True):
        if _is_sensitive_query_key(key):
            safe_items.append((key, "<redacted>"))
        else:
            safe_items.append((key, value[:_MAX_QUERY_VALUE_LENGTH]))
    return urlencode(safe_items, doseq=True)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log one concise, safe line for each HTTP request."""

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        started_at = perf_counter()
        request_id = get_request_id(request)
        client_host = request.client.host if request.client else "unknown"
        safe_query = build_safe_query_string(request.url.query)

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (perf_counter() - started_at) * 1000
            logger.exception(
                "request_id=%s method=%s path=%s query=%s status_code=%s duration_ms=%.2f client_host=%s",
                request_id,
                request.method,
                request.url.path,
                safe_query,
                500,
                duration_ms,
                client_host,
            )
            raise

        duration_ms = (perf_counter() - started_at) * 1000
        logger.info(
            "request_id=%s method=%s path=%s query=%s status_code=%s duration_ms=%.2f client_host=%s",
            request_id,
            request.method,
            request.url.path,
            safe_query,
            response.status_code,
            duration_ms,
            client_host,
        )
        return response
