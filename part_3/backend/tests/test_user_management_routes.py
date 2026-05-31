"""Route tests for controlled signup and admin user management."""

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


def seed_admin_provider(conn: FakeAuthConnection) -> tuple[dict, dict]:
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
    return admin, provider


def admin_header() -> dict[str, str]:
    return {"Authorization": "Bearer admin-token"}


def provider_header() -> dict[str, str]:
    return {"Authorization": "Bearer provider-token"}


def signup_payload(username: str = "new-provider") -> dict[str, object]:
    return {
        "requested_username": username,
        "display_name": "New Provider User",
        "password": "NewProvider1!",
        "provider_id": "999999",
        "organization_name": "Local Provider",
        "message": "Please approve my access for local demo.",
    }


def test_public_signup_creates_pending_request_not_active_user_and_rejects_duplicates() -> None:
    client, conn = build_client()
    seed_admin_provider(conn)

    response = client.post("/auth/registration-requests", json=signup_payload())
    duplicate = client.post("/auth/registration-requests", json=signup_payload())
    admin_role = client.post("/auth/registration-requests", json={**signup_payload("bad-admin"), "requested_role": "admin"})

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "pending"
    assert payload["requested_role"] == "provider"
    assert "password" not in response.text
    assert "pending_password" not in response.text
    assert conn.users_by_username.get("new-provider") is None
    assert duplicate.status_code == 409
    assert admin_role.status_code == 422


def test_signup_and_admin_user_creation_reject_weak_passwords() -> None:
    client, conn = build_client()
    seed_admin_provider(conn)

    signup = client.post("/auth/registration-requests", json={**signup_payload("weak-signup"), "password": "weakpassword"})
    managed = client.post(
        "/admin/users",
        headers=admin_header(),
        json={
            "username": "weak-managed",
            "display_name": "Weak Managed",
            "role": "provider",
            "provider_id": "999999",
            "password": "weakpassword",
        },
    )

    assert signup.status_code == 422
    assert managed.status_code == 422


def test_admin_can_list_approve_request_and_new_provider_can_login() -> None:
    client, conn = build_client()
    seed_admin_provider(conn)
    request = client.post("/auth/registration-requests", json=signup_payload("approved-provider")).json()

    listed = client.get("/admin/registration-requests", headers=admin_header())
    detail = client.get(f"/admin/registration-requests/{request['id']}", headers=admin_header())
    approve = client.post(
        f"/admin/registration-requests/{request['id']}/approve",
        headers=admin_header(),
        json={"review_notes": "Approved for provider workspace demo."},
    )
    login = client.post("/auth/login", json={"username": "approved-provider", "password": "NewProvider1!"})

    assert listed.status_code == 200
    assert listed.json()["items"][0]["id"] == request["id"]
    assert detail.status_code == 200
    assert approve.status_code == 200
    assert approve.json()["status"] == "approved"
    assert approve.json()["created_user_id"] is not None
    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"


def test_admin_can_reject_registration_request_without_creating_user() -> None:
    client, conn = build_client()
    seed_admin_provider(conn)
    request = client.post("/auth/registration-requests", json=signup_payload("rejected-provider")).json()

    reject = client.post(
        f"/admin/registration-requests/{request['id']}/reject",
        headers=admin_header(),
        json={"review_notes": "Provider id could not be verified."},
    )
    login = client.post("/auth/login", json={"username": "rejected-provider", "password": "NewProvider1!"})

    assert reject.status_code == 200
    assert reject.json()["status"] == "rejected"
    assert reject.json()["created_user_id"] is None
    assert login.status_code == 401


def test_admin_user_management_create_update_deactivate_reactivate_reset_and_sessions() -> None:
    client, conn = build_client()
    seed_admin_provider(conn)

    created = client.post(
        "/admin/users",
        headers=admin_header(),
        json={
            "username": "managed-provider",
            "display_name": "Managed Provider",
            "role": "provider",
            "provider_id": "999999",
            "password": "ManagedPass1!",
        },
    )
    user_id = created.json()["id"]
    duplicate = client.post(
        "/admin/users",
        headers=admin_header(),
        json={
            "username": "managed-provider",
            "display_name": "Managed Provider",
            "role": "provider",
            "provider_id": "999999",
            "password": "ManagedPass1!",
        },
    )
    listed = client.get("/admin/users", headers=admin_header())
    patched = client.patch(f"/admin/users/{user_id}", headers=admin_header(), json={"display_name": "Managed Provider Updated"})
    token_login = client.post("/auth/login", json={"username": "managed-provider", "password": "ManagedPass1!"})
    sessions = client.get(f"/admin/users/{user_id}/sessions", headers=admin_header())
    deactivate = client.post(f"/admin/users/{user_id}/deactivate", headers=admin_header())
    blocked_login = client.post("/auth/login", json={"username": "managed-provider", "password": "ManagedPass1!"})
    reactivate = client.post(f"/admin/users/{user_id}/reactivate", headers=admin_header())
    reset = client.post(
        f"/admin/users/{user_id}/reset-password",
        headers=admin_header(),
        json={"new_password": "ManagedNewPass1!", "revoke_existing_sessions": True},
    )
    new_login = client.post("/auth/login", json={"username": "managed-provider", "password": "ManagedNewPass1!"})

    assert created.status_code == 201
    assert "password_hash" not in created.text
    assert "password_salt" not in created.text
    assert duplicate.status_code == 409
    assert listed.status_code == 200
    assert any(item["username"] == "managed-provider" for item in listed.json()["items"])
    assert patched.status_code == 200
    assert patched.json()["display_name"] == "Managed Provider Updated"
    assert token_login.status_code == 200
    assert sessions.status_code == 200
    assert sessions.json()["items"]
    assert deactivate.status_code == 200
    assert blocked_login.status_code == 401
    assert reactivate.status_code == 200
    assert reset.status_code == 200
    assert "ManagedNewPass1!" not in reset.text
    assert new_login.status_code == 200


def test_provider_api_key_and_missing_token_cannot_access_user_management_or_request_review() -> None:
    client, conn = build_client()
    seed_admin_provider(conn)

    missing = client.get("/admin/users", headers={REQUEST_ID_HEADER: "missing-user-admin"})
    provider = client.get("/admin/users", headers=provider_header())
    api_key = client.get("/admin/registration-requests", headers={"X-API-Key": "part3_export_secret_value"})

    assert missing.status_code == 401
    assert missing.json()["error"]["request_id"] == "missing-user-admin"
    assert provider.status_code == 403
    assert api_key.status_code == 401
