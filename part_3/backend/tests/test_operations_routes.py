"""Route tests for admin-only source-monitoring and refresh operations."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.auth.models import Role
from backend.app.dependencies import get_db_connection
from backend.app.main import create_app
from backend.app.source_monitor import routes
from backend.tests.auth_test_utils import FakeAuthConnection, override_db


def build_client(conn: FakeAuthConnection | None = None) -> tuple[TestClient, FakeAuthConnection]:
    fake_conn = conn or FakeAuthConnection()
    app = create_app(run_startup_seeder=False)
    app.dependency_overrides[get_db_connection] = override_db(fake_conn)
    return TestClient(app), fake_conn


def add_admin_and_provider_tokens(conn: FakeAuthConnection) -> None:
    conn.add_user(username="admin", password="admin-password", role=Role.ADMIN, display_name="Local Admin")
    conn.add_user(
        username="provider",
        password="provider-password",
        role=Role.PROVIDER,
        display_name="Local Provider",
        provider_id="999999",
    )
    conn.add_token(username="admin", raw_token="admin-token")
    conn.add_token(username="provider", raw_token="provider-token")
    conn.add_api_key(raw_api_key="part3_export", scopes=["export:read"])


def test_source_monitor_status_requires_admin_and_returns_summary(monkeypatch) -> None:
    """Admin operations status is not public and returns monitor state for admins."""
    monkeypatch.setattr(
        routes,
        "build_status",
        lambda conn: {
            "monitor_enabled": False,
            "run_on_startup": False,
            "auto_import_enabled": False,
            "interval_minutes": 360,
            "source_url": "https://example.test/myh",
            "last_check": None,
            "known_source_files": 2,
            "unread_notifications": 1,
            "latest_refresh_run": None,
        },
    )
    client, conn = build_client()
    add_admin_and_provider_tokens(conn)

    public_response = client.get("/admin/source-monitor/status")
    provider_response = client.get("/admin/source-monitor/status", headers={"Authorization": "Bearer provider-token"})
    api_key_response = client.get("/admin/source-monitor/status", headers={"X-API-Key": "part3_export"})
    admin_response = client.get("/admin/source-monitor/status", headers={"Authorization": "Bearer admin-token"})

    assert public_response.status_code == 401
    assert provider_response.status_code == 403
    assert api_key_response.status_code == 401
    assert admin_response.status_code == 200
    assert admin_response.json()["known_source_files"] == 2
    assert admin_response.json()["unread_notifications"] == 1


def test_admin_can_run_source_check(monkeypatch) -> None:
    """POST /admin/source-monitor/check should call the source monitor service."""
    called = {}

    def fake_run_source_check(conn, *, actor_user_id=None):
        called["actor_user_id"] = actor_user_id
        return {
            "check_run_id": "11111111-1111-1111-1111-111111111111",
            "status": "success",
            "source_url": "https://example.test/myh",
            "started_at": "2030-01-01T00:00:00Z",
            "finished_at": "2030-01-01T00:00:02Z",
            "http_status": 200,
            "discovered_count": 1,
            "new_count": 1,
            "changed_count": 0,
            "known_count": 0,
            "message": "Source check completed: 1 new, 0 changed, 0 known file(s).",
            "error_message": None,
            "files": [],
        }

    monkeypatch.setattr(routes, "run_source_check", fake_run_source_check)
    client, conn = build_client()
    add_admin_and_provider_tokens(conn)

    response = client.post("/admin/source-monitor/check", headers={"Authorization": "Bearer admin-token"})

    assert response.status_code == 200
    assert response.json()["new_count"] == 1
    assert called["actor_user_id"]


def test_provider_and_export_key_cannot_run_source_check() -> None:
    """Provider sessions and export API keys cannot trigger source checks."""
    client, conn = build_client()
    add_admin_and_provider_tokens(conn)

    provider_response = client.post("/admin/source-monitor/check", headers={"Authorization": "Bearer provider-token"})
    api_key_response = client.post("/admin/source-monitor/check", headers={"X-API-Key": "part3_export"})

    assert provider_response.status_code == 403
    assert api_key_response.status_code == 401


def test_download_import_and_refresh_routes_use_admin_service(monkeypatch) -> None:
    """Admin actions call the robust refresh services and keep POST /refresh admin-only."""
    source_file_id = "22222222-2222-2222-2222-222222222222"
    refresh_run_id = "33333333-3333-3333-3333-333333333333"

    monkeypatch.setattr(
        routes,
        "download_source_file",
        lambda conn, *, source_file_id: {
            "source_file_id": source_file_id,
            "file_name": "resultat-2026.xlsx",
            "downloaded_path": "backend/runtime/source_files/resultat-2026.xlsx",
            "sha256": "a" * 64,
            "size_bytes": 100,
            "changed": False,
            "message": "Source file downloaded and hashed.",
        },
    )
    monkeypatch.setattr(
        routes,
        "import_source_file",
        lambda conn, *, source_file_id, actor_user_id: {
            "id": refresh_run_id,
            "source_file_id": source_file_id,
            "status": "success",
            "mode": "official_source_file",
            "started_at": "2030-01-01T00:00:00Z",
            "finished_at": "2030-01-01T00:00:03Z",
            "rows_imported": 1,
            "affected_years": "2026",
            "source_sha256": "a" * 64,
            "downloaded_path": "backend/runtime/source_files/resultat-2026.xlsx",
            "processed_path": "backend/runtime/processed/refresh.csv",
            "validation_summary": "Validated 1 rows for source year(s): 2026.",
            "error_message": None,
            "triggered_by_user_id": actor_user_id,
        },
    )
    monkeypatch.setattr(
        routes,
        "refresh_from_curated_csv_compatibility",
        lambda conn, *, actor_user_id: {
            "id": refresh_run_id,
            "source_file_id": None,
            "status": "success",
            "mode": "curated_csv_compatibility",
            "started_at": "2030-01-01T00:00:00Z",
            "finished_at": "2030-01-01T00:00:03Z",
            "rows_imported": 7641,
            "affected_years": "2020,2021,2022,2023,2024,2025",
            "source_sha256": "b" * 64,
            "downloaded_path": "part_2/data/processed/myh_curated_applications_2020_2025.csv",
            "processed_path": "backend/runtime/processed/refresh.csv",
            "validation_summary": "Validated 7641 rows.",
            "error_message": None,
            "triggered_by_user_id": actor_user_id,
        },
    )
    client, conn = build_client()
    add_admin_and_provider_tokens(conn)
    headers = {"Authorization": "Bearer admin-token"}

    download_response = client.post(f"/admin/source-files/{source_file_id}/download", headers=headers)
    import_response = client.post(f"/admin/source-files/{source_file_id}/import", headers=headers)
    refresh_response = client.post("/refresh", headers=headers)
    provider_refresh = client.post("/refresh", headers={"Authorization": "Bearer provider-token"})

    assert download_response.status_code == 200
    assert download_response.json()["sha256"] == "a" * 64
    assert import_response.status_code == 200
    assert import_response.json()["affected_years"] == "2026"
    assert refresh_response.status_code == 200
    assert refresh_response.json()["mode"] == "curated_csv_compatibility"
    assert provider_refresh.status_code == 403


def test_admin_can_mark_notifications(monkeypatch) -> None:
    """Admin notifications can be marked read/resolved."""
    notification_id = "44444444-4444-4444-4444-444444444444"

    def fake_update(conn, *, notification_id, status, actor_user_id):
        return {
            "id": str(notification_id),
            "notification_type": "source_file_detected",
            "severity": "info",
            "title": "New official MYH source file detected",
            "message": "resultat-2026.xlsx was discovered.",
            "status": status,
            "source_file_id": None,
            "refresh_run_id": None,
            "created_at": "2030-01-01T00:00:00Z",
            "read_at": "2030-01-01T00:00:01Z" if status == "read" else None,
            "resolved_at": "2030-01-01T00:00:01Z" if status == "resolved" else None,
            "actor_user_id": actor_user_id,
        }

    monkeypatch.setattr(routes.repo, "update_notification_status", fake_update)
    client, conn = build_client()
    add_admin_and_provider_tokens(conn)

    read_response = client.post(f"/admin/notifications/{notification_id}/read", headers={"Authorization": "Bearer admin-token"})
    resolve_response = client.post(f"/admin/notifications/{notification_id}/resolve", headers={"Authorization": "Bearer admin-token"})

    assert read_response.status_code == 200
    assert read_response.json()["status"] == "read"
    assert resolve_response.status_code == 200
    assert resolve_response.json()["status"] == "resolved"
