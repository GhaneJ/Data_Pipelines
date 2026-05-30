"""Small API route-registration tests that do not require a live database."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_root_and_lightweight_health_endpoints() -> None:
    """The always-lightweight endpoints should work without PostgreSQL."""
    client = TestClient(create_app(run_startup_seeder=False))

    root = client.get("/")
    assert root.status_code == 200
    assert root.json()["service"] == "MYH Applications API"
    assert root.json()["status"] == "ok"

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}


def test_expected_routes_are_registered() -> None:
    """The refactor should keep the existing public API surface registered."""
    app = create_app(run_startup_seeder=False)
    paths = {route.path for route in app.routes}

    expected_paths = {
        "/",
        "/health",
        "/health/db",
        "/applications",
        "/applications/{diarienummer:path}",
        "/stats/by-year",
        "/stats/by-region",
        "/stats/by-education-area",
        "/stats/by-decision",
        "/stats/trends/by-decision",
        "/stats/trends/by-region",
        "/stats/trends/by-education-area",
        "/providers",
        "/providers/{provider_id}/applications",
        "/export/applications",
        "/operations/source-status",
        "/operations/check-source",
        "/refresh",
        "/auth/whoami",
        "/admin/applications/{diarienummer:path}/notes",
        "/admin/notes/{note_id}",
        "/admin/api-keys",
        "/admin/api-keys/{key_id}/revoke",
    }

    assert expected_paths.issubset(paths)


def test_startup_calls_database_seeder(monkeypatch) -> None:
    """The real FastAPI startup path should call the database bootstrap service."""
    from backend.app import main as main_module

    calls = []
    monkeypatch.setattr(main_module, "ensure_database_ready", lambda: calls.append("seeded"))

    with TestClient(main_module.create_app()) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert calls == ["seeded"]
