"""Request-context middleware and helpers."""

from __future__ import annotations

import re
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


REQUEST_ID_HEADER = "X-Request-ID"
REQUEST_ID_STATE_ATTRIBUTE = "request_id"
_MAX_REQUEST_ID_LENGTH = 128
_SAFE_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]+$")


def generate_request_id() -> str:
    """Generate a safe request identifier for logs and responses."""
    return str(uuid4())


def normalize_request_id(value: str | None) -> str | None:
    """Return a safe caller-provided request id, or None when it is unusable.

    The API accepts practical request ids such as UUIDs or demo values like
    ``demo-request-123``. Newlines, spaces, and very long values are rejected
    so the id is safe to echo in logs and response headers.
    """
    if value is None:
        return None

    request_id = value.strip()
    if not request_id or len(request_id) > _MAX_REQUEST_ID_LENGTH:
        return None
    if not _SAFE_REQUEST_ID_PATTERN.fullmatch(request_id):
        return None
    return request_id


def get_request_id(request: Request) -> str:
    """Read the request id stored on request.state, falling back safely."""
    request_id = getattr(request.state, REQUEST_ID_STATE_ATTRIBUTE, None)
    if isinstance(request_id, str) and request_id:
        return request_id
    return generate_request_id()


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a correlation id to every request and response."""

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        request_id = normalize_request_id(request.headers.get(REQUEST_ID_HEADER)) or generate_request_id()
        setattr(request.state, REQUEST_ID_STATE_ATTRIBUTE, request_id)

        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
