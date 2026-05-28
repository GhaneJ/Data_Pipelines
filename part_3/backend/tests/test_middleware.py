"""Tests for request context and safe request logging middleware."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi.testclient import TestClient

from backend.app.main import create_app


REQUEST_ID_HEADER = "X-Request-ID"


def test_request_id_header_is_returned_when_provided() -> None:
    """Caller-provided request ids should be echoed for correlation."""
    client = TestClient(create_app(run_startup_seeder=False))

    response = client.get("/health", headers={REQUEST_ID_HEADER: "demo-request-123"})

    assert response.status_code == 200
    assert response.headers[REQUEST_ID_HEADER] == "demo-request-123"


def test_request_id_header_is_generated_when_missing() -> None:
    """Requests without a request id should receive a generated UUID value."""
    client = TestClient(create_app(run_startup_seeder=False))

    response = client.get("/health")

    assert response.status_code == 200
    generated_request_id = response.headers[REQUEST_ID_HEADER]
    assert str(UUID(generated_request_id)) == generated_request_id


def test_request_log_includes_safe_request_metadata(caplog) -> None:
    """Request logs should include useful metadata without leaking token-like values."""
    client = TestClient(create_app(run_startup_seeder=False))

    with caplog.at_level(logging.INFO, logger="backend.app.request"):
        response = client.get(
            "/health?limit=5&api_key=secret-value",
            headers={REQUEST_ID_HEADER: "log-request-123"},
        )

    assert response.status_code == 200
    log_text = "\n".join(
        record.getMessage() for record in caplog.records if record.name == "backend.app.request"
    )
    assert "request_id=log-request-123" in log_text
    assert "method=GET" in log_text
    assert "path=/health" in log_text
    assert "status_code=200" in log_text
    assert "limit=5" in log_text
    assert "api_key=%3Credacted%3E" in log_text
    assert "secret-value" not in log_text
