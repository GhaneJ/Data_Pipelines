"""CORS tests for the local React dashboard integration."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_local_dashboard_origin_is_allowed_for_public_gets() -> None:
    """The Vite dev server should be able to call public read endpoints."""
    client = TestClient(create_app(run_startup_seeder=False))

    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "GET" in response.headers["access-control-allow-methods"]


def test_unlisted_origin_is_not_allowed_by_dashboard_cors() -> None:
    """The local-dashboard CORS rule should stay narrow."""
    client = TestClient(create_app(run_startup_seeder=False))

    response = client.options(
        "/health",
        headers={
            "Origin": "http://example.com",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
