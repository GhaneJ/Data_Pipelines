"""Route tests for protected admin-note endpoints without PostgreSQL."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from backend.app.auth.models import Role
from backend.app.dependencies import get_db_connection
from backend.app.main import create_app
from backend.app.routers import admin
from backend.tests.auth_test_utils import FakeAuthConnection, override_db


REQUEST_ID_HEADER = "X-Request-ID"


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


def test_admin_route_rejects_missing_token() -> None:
    client, conn = build_client()
    add_admin_and_provider_tokens(conn)

    response = client.get("/admin/applications/MYH%202024%2F1/notes")

    assert response.status_code == 401
    payload = response.json()
    assert payload["error"]["code"] == "unauthorized"
    assert payload["detail"] == "Authentication is required."
    assert REQUEST_ID_HEADER in response.headers


def test_admin_route_rejects_invalid_bearer_token() -> None:
    client, conn = build_client()
    add_admin_and_provider_tokens(conn)

    response = client.get("/admin/applications/MYH%202024%2F1/notes", headers={"Authorization": "Bearer wrong"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_static_admin_header_no_longer_grants_access() -> None:
    """The retired local admin header must not pass the admin auth boundary."""
    client, conn = build_client()
    add_admin_and_provider_tokens(conn)

    response = client.get("/admin/applications/MYH%202024%2F1/notes", headers={"X-Admin-Token": "admin-token"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_admin_route_accepts_admin_bearer_token(monkeypatch) -> None:
    monkeypatch.setattr(admin, "list_application_notes", lambda conn, diarienummer: [])
    client, conn = build_client()
    add_admin_and_provider_tokens(conn)

    response = client.get(
        "/admin/applications/MYH%202024%2F1/notes",
        headers={"Authorization": "Bearer admin-token"},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_admin_route_rejects_provider_bearer_token_with_403() -> None:
    client, conn = build_client()
    add_admin_and_provider_tokens(conn)

    response = client.get(
        "/admin/applications/MYH%202024%2F1/notes",
        headers={"Authorization": "Bearer provider-token", REQUEST_ID_HEADER: "provider-admin-123"},
    )

    assert response.status_code == 403
    assert response.headers[REQUEST_ID_HEADER] == "provider-admin-123"
    payload = response.json()
    assert payload["error"]["code"] == "forbidden"
    assert payload["error"]["request_id"] == "provider-admin-123"
    assert "provider-token" not in response.text


def test_list_admin_notes_accepts_admin_token(monkeypatch) -> None:
    monkeypatch.setattr(
        admin,
        "list_application_notes",
        lambda conn, diarienummer: [
            {
                "id": 1,
                "diarienummer": diarienummer,
                "note_text": "Check before demo.",
                "created_at": "2026-05-27T10:00:00+00:00",
                "updated_at": "2026-05-27T10:00:00+00:00",
            }
        ],
    )
    client, conn = build_client()
    add_admin_and_provider_tokens(conn)

    response = client.get(
        "/admin/applications/MYH%202024%2F1/notes",
        headers={"Authorization": "Bearer admin-token"},
    )

    assert response.status_code == 200
    assert response.json()[0]["diarienummer"] == "MYH 2024/1"


def test_create_admin_note_returns_400_for_blank_text() -> None:
    client, conn = build_client()
    add_admin_and_provider_tokens(conn)

    response = client.post(
        "/admin/applications/MYH%202024%2F1/notes",
        headers={"Authorization": "Bearer admin-token"},
        json={"note_text": "   "},
    )

    assert response.status_code == 400
    assert "note_text" in response.json()["detail"]


def test_create_admin_note_returns_404_for_missing_application(monkeypatch) -> None:
    monkeypatch.setattr(admin, "create_application_note", lambda conn, diarienummer, note_text: None)
    client, conn = build_client()
    add_admin_and_provider_tokens(conn)

    response = client.post(
        "/admin/applications/MISSING/notes",
        headers={"Authorization": "Bearer admin-token"},
        json={"note_text": "Follow up."},
    )

    assert response.status_code == 404
    assert "Application" in response.json()["detail"]


def test_create_update_and_delete_admin_note_with_mocked_service(monkeypatch) -> None:
    created_note: dict[str, Any] = {
        "id": 3,
        "diarienummer": "MYH 2024/1",
        "note_text": "Follow up.",
        "created_at": "2026-05-27T10:00:00+00:00",
        "updated_at": "2026-05-27T10:00:00+00:00",
    }
    updated_note = {**created_note, "note_text": "Updated follow up."}
    monkeypatch.setattr(admin, "create_application_note", lambda conn, diarienummer, note_text: created_note)
    monkeypatch.setattr(admin, "update_application_note", lambda conn, note_id, note_text: updated_note)
    monkeypatch.setattr(admin, "delete_application_note", lambda conn, note_id: True)
    client, conn = build_client()
    add_admin_and_provider_tokens(conn)
    headers = {"Authorization": "Bearer admin-token"}

    create_response = client.post(
        "/admin/applications/MYH%202024%2F1/notes",
        headers=headers,
        json={"note_text": "Follow up."},
    )
    update_response = client.put("/admin/notes/3", headers=headers, json={"note_text": "Updated follow up."})
    patch_response = client.patch("/admin/notes/3", headers=headers, json={"note_text": "Updated follow up."})
    delete_response = client.delete("/admin/notes/3", headers=headers)

    assert create_response.status_code == 201
    assert create_response.json()["id"] == 3
    assert update_response.status_code == 200
    assert update_response.json()["note_text"] == "Updated follow up."
    assert patch_response.status_code == 200
    assert patch_response.json()["note_text"] == "Updated follow up."
    assert delete_response.status_code == 200
    assert delete_response.json() == {"note_id": 3, "deleted": True}


def test_update_admin_note_returns_404_when_note_missing(monkeypatch) -> None:
    monkeypatch.setattr(admin, "update_application_note", lambda conn, note_id, note_text: None)
    client, conn = build_client()
    add_admin_and_provider_tokens(conn)

    response = client.put(
        "/admin/notes/999",
        headers={"Authorization": "Bearer admin-token"},
        json={"note_text": "Updated."},
    )

    assert response.status_code == 404
    assert "Admin note" in response.json()["detail"]


def test_patch_admin_note_returns_400_for_empty_patch_body() -> None:
    client, conn = build_client()
    add_admin_and_provider_tokens(conn)

    response = client.patch("/admin/notes/3", headers={"Authorization": "Bearer admin-token"}, json={})

    assert response.status_code == 400
    assert "note_text" in response.json()["detail"]


def test_patch_admin_note_returns_404_when_note_missing(monkeypatch) -> None:
    monkeypatch.setattr(admin, "update_application_note", lambda conn, note_id, note_text: None)
    client, conn = build_client()
    add_admin_and_provider_tokens(conn)

    response = client.patch(
        "/admin/notes/999",
        headers={"Authorization": "Bearer admin-token"},
        json={"note_text": "Updated."},
    )

    assert response.status_code == 404
    assert "Admin note" in response.json()["detail"]
