"""Tests for source-check operation routes without live internet or PostgreSQL."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.routers import operations


def test_source_status_route_returns_manifest_payload(monkeypatch) -> None:
    """GET /operations/source-status should read the local manifest only."""
    monkeypatch.setattr(
        operations,
        "read_source_status_manifest",
        lambda: {
            "checked_at": None,
            "source_url": "https://example.test",
            "status": "not_checked",
            "http_status": None,
            "content_type": None,
            "discovered_files": [],
            "configured_files": [],
            "known_latest_source_snapshot": None,
            "local_latest_source_year": None,
            "up_to_date": None,
            "message": "No source check has been recorded yet.",
            "error": None,
        },
    )

    client = TestClient(create_app(run_startup_seeder=False))
    response = client.get("/operations/source-status")

    assert response.status_code == 200
    assert response.json()["status"] == "not_checked"


def test_check_source_route_uses_service(monkeypatch) -> None:
    """POST /operations/check-source should call the source-check service."""
    monkeypatch.setattr(
        operations,
        "run_source_check",
        lambda write_manifest=True: {
            "checked_at": "2026-05-27T10:00:00+00:00",
            "source_url": "https://example.test",
            "status": "up_to_date",
            "http_status": 200,
            "content_type": "text/html",
            "discovered_files": [],
            "configured_files": [],
            "known_latest_source_snapshot": 2025,
            "local_latest_source_year": 2025,
            "up_to_date": True,
            "message": "OK",
            "error": None,
        },
    )

    client = TestClient(create_app(run_startup_seeder=False))
    response = client.post("/operations/check-source")

    assert response.status_code == 200
    assert response.json()["status"] == "up_to_date"


def test_refresh_can_require_recent_source_check(monkeypatch) -> None:
    """Refresh should reject an explicit recent-source-check requirement when no check exists."""
    monkeypatch.setattr(
        operations,
        "read_source_status_manifest",
        lambda: {
            "checked_at": None,
            "source_url": "https://example.test",
            "status": "not_checked",
            "http_status": None,
            "content_type": None,
            "discovered_files": [],
            "configured_files": [],
            "known_latest_source_snapshot": None,
            "local_latest_source_year": None,
            "up_to_date": None,
            "message": "No source check has been recorded yet.",
            "error": None,
        },
    )

    client = TestClient(create_app(run_startup_seeder=False))
    response = client.post("/refresh?require_recent_source_check=true")

    assert response.status_code == 400
    assert "Run POST /operations/check-source" in response.json()["detail"]
