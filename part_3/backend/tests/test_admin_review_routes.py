"""Route tests for admin review and decision workflow."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.auth.models import Role
from backend.app.dependencies import get_db_connection
from backend.app.main import create_app
from backend.tests.auth_test_utils import FakeAuthConnection, override_db

REQUEST_ID_HEADER = "X-Request-ID"


def build_client() -> tuple[TestClient, FakeAuthConnection]:
    conn = FakeAuthConnection()
    app = create_app(run_startup_seeder=False)
    app.dependency_overrides[get_db_connection] = override_db(conn)
    return TestClient(app), conn


def seed_auth(conn: FakeAuthConnection) -> dict[str, dict]:
    admin = conn.add_user(username="admin", password="admin-password", role=Role.ADMIN, display_name="Local Admin")
    provider = conn.add_user(
        username="provider",
        password="provider-password",
        role=Role.PROVIDER,
        display_name="Local Provider",
        provider_id="999999",
    )
    conn.add_token(username="admin", raw_token="admin-token")
    conn.add_token(username="provider", raw_token="provider-token")
    conn.add_api_key(raw_api_key="part3_export_secret_value", scopes=["export:read"], created_by_user_id=admin["id"])
    return {"admin": admin, "provider": provider}


def admin_header() -> dict[str, str]:
    return {"Authorization": "Bearer admin-token"}


def provider_header() -> dict[str, str]:
    return {"Authorization": "Bearer provider-token"}


def test_admin_can_list_read_review_and_approve_provider_submission() -> None:
    client, conn = build_client()
    users = seed_auth(conn)
    submitted = conn.add_provider_submission(provider_id="999999", created_by_user_id=users["provider"]["id"], status="submitted")
    draft = conn.add_provider_submission(provider_id="999999", created_by_user_id=users["provider"]["id"], status="draft")

    listed = client.get("/admin/provider-submissions", headers=admin_header())
    detail = client.get(f"/admin/provider-submissions/{submitted['id']}", headers=admin_header())
    start = client.post(
        f"/admin/provider-submissions/{submitted['id']}/start-review",
        headers=admin_header(),
        json={"review_notes": "Initial admin review started."},
    )
    approve = client.post(
        f"/admin/provider-submissions/{submitted['id']}/approve",
        headers=admin_header(),
        json={"review_notes": "Approved for workflow demo."},
    )
    events = client.get(f"/admin/provider-submissions/{submitted['id']}/events", headers=admin_header())
    invalid_transition = client.post(f"/admin/provider-submissions/{draft['id']}/approve", headers=admin_header(), json={})

    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["items"]] == [submitted["id"]]
    assert detail.status_code == 200
    assert detail.json()["id"] == submitted["id"]
    assert start.status_code == 200
    assert start.json()["status"] == "under_review"
    assert approve.status_code == 200
    assert approve.json()["status"] == "approved"
    assert approve.json()["reviewed_by_user_id"] == users["admin"]["id"]
    assert events.status_code == 200
    assert [event["action"] for event in events.json()] == ["review_started", "approved"]
    assert invalid_transition.status_code == 409
    assert invalid_transition.json()["error"]["code"] == "conflict"


def test_admin_can_request_changes_and_provider_can_correct_and_resubmit() -> None:
    client, conn = build_client()
    users = seed_auth(conn)
    submitted = conn.add_provider_submission(provider_id="999999", created_by_user_id=users["provider"]["id"], status="submitted")

    request_changes = client.post(
        f"/admin/provider-submissions/{submitted['id']}/request-changes",
        headers=admin_header(),
        json={"review_notes": "Please clarify study pace."},
    )
    provider_update = client.patch(
        f"/provider/submissions/{submitted['id']}",
        headers=provider_header(),
        json={"notes": "Clarified requested details.", "study_pace_percent": 75},
    )
    resubmit = client.post(f"/provider/submissions/{submitted['id']}/submit", headers=provider_header())

    assert request_changes.status_code == 200
    assert request_changes.json()["status"] == "needs_changes"
    assert request_changes.json()["review_notes"] == "Please clarify study pace."
    assert provider_update.status_code == 200
    assert provider_update.json()["status"] == "needs_changes"
    assert provider_update.json()["study_pace_percent"] == 75
    assert resubmit.status_code == 200
    assert resubmit.json()["status"] == "submitted"


def test_admin_review_auth_boundaries_are_enforced() -> None:
    client, conn = build_client()
    seed_auth(conn)

    missing = client.get("/admin/provider-submissions", headers={REQUEST_ID_HEADER: "missing-admin-review-auth"})
    invalid = client.get("/admin/provider-submissions", headers={"Authorization": "Bearer wrong-token"})
    provider = client.get("/admin/provider-submissions", headers=provider_header())
    api_key = client.get("/admin/provider-submissions", headers={"X-API-Key": "part3_export_secret_value"})
    legacy_admin_header = client.get("/admin/provider-submissions", headers={"X-Admin-Token": "legacy-admin-token"})

    assert missing.status_code == 401
    assert missing.headers[REQUEST_ID_HEADER] == "missing-admin-review-auth"
    assert missing.json()["error"]["request_id"] == "missing-admin-review-auth"
    assert invalid.status_code == 401
    assert provider.status_code == 403
    assert api_key.status_code == 401
    assert legacy_admin_header.status_code == 401


def test_missing_submission_and_invalid_uuid_use_standard_errors() -> None:
    client, conn = build_client()
    seed_auth(conn)

    missing = client.get(
        "/admin/provider-submissions/00000000-0000-0000-0000-000000000000",
        headers={**admin_header(), REQUEST_ID_HEADER: "missing-submission-123"},
    )
    invalid_uuid = client.get(
        "/admin/provider-submissions/not-a-uuid",
        headers={**admin_header(), REQUEST_ID_HEADER: "bad-admin-review-uuid"},
    )

    assert missing.status_code == 404
    assert missing.json()["error"]["request_id"] == "missing-submission-123"
    assert invalid_uuid.status_code == 422
    assert invalid_uuid.json()["error"]["request_id"] == "bad-admin-review-uuid"
