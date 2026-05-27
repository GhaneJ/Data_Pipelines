"""Route tests for protected admin-note endpoints without PostgreSQL."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from backend.app.dependencies import get_db_connection
from backend.app.main import create_app
from backend.app.routers import admin
from backend.app.security import ADMIN_TOKEN_ENV_VAR


class DummyConnection:
    """Placeholder connection because service calls are monkeypatched."""


def override_db_connection() -> Iterator[DummyConnection]:
    """Provide a DB dependency override for admin route tests."""
    yield DummyConnection()


def build_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Create a TestClient with admin auth configured and database mocked."""
    monkeypatch.setenv(ADMIN_TOKEN_ENV_VAR, "test-token")
    app = create_app()
    app.dependency_overrides[get_db_connection] = override_db_connection
    return TestClient(app)


def test_admin_route_rejects_missing_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Protected admin routes should not be public."""
    client = build_client(monkeypatch)

    response = client.get("/admin/applications/MYH%202024%2F1/notes")

    assert response.status_code == 401
    assert "X-Admin-Token" in response.json()["detail"]


def test_admin_route_rejects_wrong_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Wrong admin tokens should not reach the service layer."""
    client = build_client(monkeypatch)

    response = client.get("/admin/applications/MYH%202024%2F1/notes", headers={"X-Admin-Token": "wrong"})

    assert response.status_code == 403


def test_list_admin_notes_accepts_correct_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """A correct token should allow protected read access to local notes."""
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
    client = build_client(monkeypatch)

    response = client.get("/admin/applications/MYH%202024%2F1/notes", headers={"X-Admin-Token": "test-token"})

    assert response.status_code == 200
    assert response.json()[0]["diarienummer"] == "MYH 2024/1"


def test_create_admin_note_returns_400_for_blank_text(monkeypatch: pytest.MonkeyPatch) -> None:
    """Empty notes should be rejected with the documented 400 status."""
    client = build_client(monkeypatch)

    response = client.post(
        "/admin/applications/MYH%202024%2F1/notes",
        headers={"X-Admin-Token": "test-token"},
        json={"note_text": "   "},
    )

    assert response.status_code == 400
    assert "note_text" in response.json()["detail"]


def test_create_admin_note_returns_404_for_missing_application(monkeypatch: pytest.MonkeyPatch) -> None:
    """Writes should validate the application before creating local metadata."""
    monkeypatch.setattr(admin, "create_application_note", lambda conn, diarienummer, note_text: None)
    client = build_client(monkeypatch)

    response = client.post(
        "/admin/applications/MISSING/notes",
        headers={"X-Admin-Token": "test-token"},
        json={"note_text": "Follow up."},
    )

    assert response.status_code == 404
    assert "Application" in response.json()["detail"]


def test_create_update_and_delete_admin_note_with_mocked_service(monkeypatch: pytest.MonkeyPatch) -> None:
    """The admin CRUD routes should return the service-layer payloads."""
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
    client = build_client(monkeypatch)
    headers = {"X-Admin-Token": "test-token"}

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


def test_update_admin_note_returns_404_when_note_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Updating a missing note should be clear."""
    monkeypatch.setattr(admin, "update_application_note", lambda conn, note_id, note_text: None)
    client = build_client(monkeypatch)

    response = client.put("/admin/notes/999", headers={"X-Admin-Token": "test-token"}, json={"note_text": "Updated."})

    assert response.status_code == 404
    assert "Admin note" in response.json()["detail"]


def test_patch_admin_note_returns_400_for_empty_patch_body(monkeypatch: pytest.MonkeyPatch) -> None:
    """PATCH should reject empty bodies because there is no field to update."""
    client = build_client(monkeypatch)

    response = client.patch("/admin/notes/3", headers={"X-Admin-Token": "test-token"}, json={})

    assert response.status_code == 400
    assert "note_text" in response.json()["detail"]


def test_patch_admin_note_returns_404_when_note_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """PATCH should return the same clear missing-note behavior as PUT."""
    monkeypatch.setattr(admin, "update_application_note", lambda conn, note_id, note_text: None)
    client = build_client(monkeypatch)

    response = client.patch("/admin/notes/999", headers={"X-Admin-Token": "test-token"}, json={"note_text": "Updated."})

    assert response.status_code == 404
    assert "Admin note" in response.json()["detail"]
