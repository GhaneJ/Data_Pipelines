"""Tests for standardized API error responses."""

from __future__ import annotations

from collections.abc import Iterator

from fastapi.testclient import TestClient

from backend.app.dependencies import get_db_connection
from backend.app.main import create_app


class DummyConnection:
    """Placeholder connection for route tests that should not reach PostgreSQL."""


def override_db_connection() -> Iterator[DummyConnection]:
    """Provide a DB dependency override for error-handler tests."""
    yield DummyConnection()


def build_client_with_dummy_db() -> TestClient:
    """Create a test client with the database dependency mocked."""
    app = create_app(run_startup_seeder=False)
    app.dependency_overrides[get_db_connection] = override_db_connection
    return TestClient(app)


REQUEST_ID_HEADER = "X-Request-ID"


def test_unknown_route_returns_safe_error_envelope_with_request_id() -> None:
    """404 responses should use the standard error envelope."""
    client = TestClient(create_app(run_startup_seeder=False))

    response = client.get("/does-not-exist", headers={REQUEST_ID_HEADER: "missing-route-123"})

    assert response.status_code == 404
    assert response.headers[REQUEST_ID_HEADER] == "missing-route-123"
    payload = response.json()
    assert payload["error"] == {
        "code": "not_found",
        "message": "Not Found",
        "request_id": "missing-route-123",
    }
    assert payload["detail"] == "Not Found"


def test_validation_error_returns_safe_error_envelope_with_request_id() -> None:
    """Query validation failures should keep 422 while using the new envelope."""
    client = build_client_with_dummy_db()

    response = client.get("/applications?limit=wrong", headers={REQUEST_ID_HEADER: "validation-123"})

    assert response.status_code == 422
    assert response.headers[REQUEST_ID_HEADER] == "validation-123"
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["message"] == "Request validation failed."
    assert payload["error"]["request_id"] == "validation-123"
    assert payload["detail"] == "Request validation failed."
    assert payload["error"]["invalid_params"]


def test_protected_admin_route_without_token_still_rejects_access() -> None:
    """The standardized envelope must not weaken protected admin behavior."""
    client = build_client_with_dummy_db()

    response = client.get("/admin/applications/MYH%202024%2F1/notes", headers={REQUEST_ID_HEADER: "admin-123"})

    assert response.status_code == 401
    payload = response.json()
    assert payload["error"]["code"] == "unauthorized"
    assert payload["error"]["request_id"] == "admin-123"
    assert payload["error"]["message"] == "Authentication is required."
    assert payload["detail"] == "Authentication is required."


def test_unhandled_exception_returns_safe_error_envelope() -> None:
    """Unexpected errors should not expose stack traces or exception text."""
    app = create_app(run_startup_seeder=False)

    @app.get("/test-only-boom")
    def boom() -> None:
        raise RuntimeError("secret internal failure detail")

    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/test-only-boom", headers={REQUEST_ID_HEADER: "boom-123"})

    assert response.status_code == 500
    assert response.headers[REQUEST_ID_HEADER] == "boom-123"
    payload = response.json()
    assert payload["error"] == {
        "code": "internal_server_error",
        "message": "An internal server error occurred.",
        "request_id": "boom-123",
    }
    assert "secret internal failure detail" not in response.text
