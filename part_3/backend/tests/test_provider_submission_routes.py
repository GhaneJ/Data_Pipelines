"""Route tests for provider-authenticated application submissions."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.api_keys.key_utils import hash_api_key
from backend.app.auth.models import Role
from backend.app.dependencies import get_db_connection
from backend.app.main import create_app
from backend.tests.auth_test_utils import FakeAuthConnection, override_db

REQUEST_ID_HEADER = "X-Request-ID"


def build_client(conn: FakeAuthConnection | None = None) -> tuple[TestClient, FakeAuthConnection]:
    fake_conn = conn or FakeAuthConnection()
    app = create_app(run_startup_seeder=False)
    app.dependency_overrides[get_db_connection] = override_db(fake_conn)
    return TestClient(app), fake_conn


def add_users_and_tokens(conn: FakeAuthConnection) -> dict[str, dict]:
    admin = conn.add_user(username="admin", password="admin-password", role=Role.ADMIN, display_name="Local Admin")
    provider = conn.add_user(
        username="provider",
        password="provider-password",
        role=Role.PROVIDER,
        display_name="Local Provider",
        provider_id="999999",
    )
    other_provider = conn.add_user(
        username="other-provider",
        password="provider-password",
        role=Role.PROVIDER,
        display_name="Other Provider",
        provider_id="888888",
    )
    conn.add_token(username="admin", raw_token="admin-token")
    conn.add_token(username="provider", raw_token="provider-token")
    conn.add_token(username="other-provider", raw_token="other-provider-token")
    conn.add_provider_name("999999", "Curated Provider Name")
    return {"admin": admin, "provider": provider, "other_provider": other_provider}


def valid_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "target_year": 2026,
        "education_name": "Cloud Data Engineer",
        "education_area": "Data/IT",
        "municipality": "Stockholm",
        "region": "Stockholms län",
        "yh_points": 400,
        "study_form": "Distans",
        "study_pace_percent": 100,
        "head_provider_type": "Privat",
        "description": "Provider-created draft application for future review.",
        "notes": "Initial local validation draft.",
    }
    payload.update(overrides)
    return payload


def auth_header(token: str = "provider-token") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_provider_can_create_submission_and_response_has_request_id() -> None:
    client, conn = build_client()
    users = add_users_and_tokens(conn)

    response = client.post(
        "/provider/submissions",
        headers={**auth_header(), REQUEST_ID_HEADER: "create-provider-submission-123"},
        json=valid_payload(education_name="  Cloud Data Engineer  "),
    )

    assert response.status_code == 201
    assert response.headers[REQUEST_ID_HEADER] == "create-provider-submission-123"
    payload = response.json()
    assert payload["status"] == "draft"
    assert payload["provider_id"] == "999999"
    assert payload["provider_name"] == "Curated Provider Name"
    assert payload["created_by_user_id"] == users["provider"]["id"]
    assert payload["education_name"] == "Cloud Data Engineer"


def test_missing_invalid_admin_and_api_key_do_not_access_provider_routes() -> None:
    client, conn = build_client()
    users = add_users_and_tokens(conn)
    raw_api_key = "part3_export_secret_value"
    conn.add_api_key(raw_api_key=raw_api_key, scopes=["export:read"], created_by_user_id=users["admin"]["id"])

    missing = client.get("/provider/submissions", headers={REQUEST_ID_HEADER: "missing-provider-auth-123"})
    invalid = client.get("/provider/submissions", headers={"Authorization": "Bearer wrong"})
    admin = client.get("/provider/submissions", headers={"Authorization": "Bearer admin-token"})
    api_key_only = client.get("/provider/submissions", headers={"X-API-Key": raw_api_key})

    assert missing.status_code == 401
    assert missing.json()["error"]["request_id"] == "missing-provider-auth-123"
    assert invalid.status_code == 401
    assert admin.status_code == 403
    assert api_key_only.status_code == 401


def test_provider_can_list_only_own_submissions() -> None:
    client, conn = build_client()
    users = add_users_and_tokens(conn)
    own = conn.add_provider_submission(provider_id="999999", created_by_user_id=users["provider"]["id"], status="draft")
    conn.add_provider_submission(provider_id="888888", created_by_user_id=users["other_provider"]["id"], status="draft")

    response = client.get("/provider/submissions", headers=auth_header())

    assert response.status_code == 200
    payload = response.json()
    assert payload["limit"] == 50
    assert payload["offset"] == 0
    assert [item["id"] for item in payload["items"]] == [own["id"]]


def test_provider_can_filter_list_by_status_and_target_year() -> None:
    client, conn = build_client()
    users = add_users_and_tokens(conn)
    draft = conn.add_provider_submission(provider_id="999999", created_by_user_id=users["provider"]["id"], status="draft", target_year=2026)
    conn.add_provider_submission(provider_id="999999", created_by_user_id=users["provider"]["id"], status="submitted", target_year=2025)

    response = client.get("/provider/submissions?status=draft&target_year=2026", headers=auth_header())

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == [draft["id"]]


def test_provider_can_read_own_submission_and_other_provider_returns_404() -> None:
    client, conn = build_client()
    users = add_users_and_tokens(conn)
    own = conn.add_provider_submission(provider_id="999999", created_by_user_id=users["provider"]["id"])
    other = conn.add_provider_submission(provider_id="888888", created_by_user_id=users["other_provider"]["id"])

    read_own = client.get(f"/provider/submissions/{own['id']}", headers=auth_header())
    read_other = client.get(f"/provider/submissions/{other['id']}", headers={**auth_header(), REQUEST_ID_HEADER: "other-provider-404"})

    assert read_own.status_code == 200
    assert read_own.json()["id"] == own["id"]
    assert read_other.status_code == 404
    assert read_other.json()["error"]["code"] == "not_found"
    assert read_other.json()["error"]["request_id"] == "other-provider-404"


def test_provider_can_update_draft_and_cannot_tamper_with_status() -> None:
    client, conn = build_client()
    users = add_users_and_tokens(conn)
    draft = conn.add_provider_submission(provider_id="999999", created_by_user_id=users["provider"]["id"], status="draft")

    updated = client.patch(
        f"/provider/submissions/{draft['id']}",
        headers=auth_header(),
        json={"notes": "Updated local validation note.", "study_pace_percent": 75},
    )
    tampered = client.patch(
        f"/provider/submissions/{draft['id']}",
        headers=auth_header(),
        json={"status": "submitted"},
    )

    assert updated.status_code == 200
    assert updated.json()["notes"] == "Updated local validation note."
    assert updated.json()["study_pace_percent"] == 75
    assert tampered.status_code == 422
    assert tampered.json()["error"]["code"] == "validation_error"


def test_provider_cannot_update_or_delete_submitted_submission() -> None:
    client, conn = build_client()
    users = add_users_and_tokens(conn)
    submitted = conn.add_provider_submission(provider_id="999999", created_by_user_id=users["provider"]["id"], status="submitted")

    update_response = client.patch(
        f"/provider/submissions/{submitted['id']}",
        headers={**auth_header(), REQUEST_ID_HEADER: "submitted-update-123"},
        json={"notes": "Should fail"},
    )
    delete_response = client.delete(f"/provider/submissions/{submitted['id']}", headers=auth_header())

    assert update_response.status_code == 409
    assert update_response.json()["error"]["code"] == "conflict"
    assert update_response.json()["error"]["request_id"] == "submitted-update-123"
    assert delete_response.status_code == 409


def test_provider_can_delete_own_draft() -> None:
    client, conn = build_client()
    users = add_users_and_tokens(conn)
    draft = conn.add_provider_submission(provider_id="999999", created_by_user_id=users["provider"]["id"], status="draft")

    response = client.delete(f"/provider/submissions/{draft['id']}", headers=auth_header())

    assert response.status_code == 204
    assert draft["id"] not in conn.provider_submissions_by_id


def test_provider_can_submit_draft_and_submitting_again_fails_cleanly() -> None:
    client, conn = build_client()
    users = add_users_and_tokens(conn)
    draft = conn.add_provider_submission(provider_id="999999", created_by_user_id=users["provider"]["id"], status="draft")

    submitted = client.post(f"/provider/submissions/{draft['id']}/submit", headers=auth_header())
    submitted_again = client.post(f"/provider/submissions/{draft['id']}/submit", headers=auth_header())
    edit_after_submit = client.patch(f"/provider/submissions/{draft['id']}", headers=auth_header(), json={"notes": "Too late"})

    assert submitted.status_code == 200
    assert submitted.json()["status"] == "submitted"
    assert submitted.json()["submitted_at"] is not None
    assert submitted_again.status_code == 409
    assert edit_after_submit.status_code == 409


def test_invalid_payload_and_invalid_uuid_use_standard_error_envelope() -> None:
    client, _ = build_client()
    add_users_and_tokens(_)

    bad_payload = client.post(
        "/provider/submissions",
        headers={**auth_header(), REQUEST_ID_HEADER: "bad-payload-123"},
        json=valid_payload(education_name="   ", study_pace_percent=101),
    )
    bad_uuid = client.get("/provider/submissions/not-a-uuid", headers={**auth_header(), REQUEST_ID_HEADER: "bad-uuid-123"})

    assert bad_payload.status_code == 422
    assert bad_payload.json()["error"]["code"] == "validation_error"
    assert bad_payload.json()["error"]["request_id"] == "bad-payload-123"
    assert bad_uuid.status_code == 422
    assert bad_uuid.json()["error"]["request_id"] == "bad-uuid-123"
    assert bad_payload.headers[REQUEST_ID_HEADER] == "bad-payload-123"


def test_user_bearer_token_does_not_grant_export_and_api_key_does_not_grant_provider_crud() -> None:
    client, conn = build_client()
    users = add_users_and_tokens(conn)
    raw_api_key = "part3_export_secret_value"
    conn.add_api_key(raw_api_key=raw_api_key, scopes=["export:read"], created_by_user_id=users["admin"]["id"])

    bearer_export = client.get("/export/applications?year=2024", headers=auth_header())
    api_key_provider = client.get("/provider/submissions", headers={"X-API-Key": raw_api_key})

    assert bearer_export.status_code == 401
    assert api_key_provider.status_code == 401
    assert hash_api_key(raw_api_key) not in bearer_export.text
    assert raw_api_key not in api_key_provider.text
