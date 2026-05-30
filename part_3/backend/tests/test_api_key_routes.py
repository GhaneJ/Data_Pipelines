"""Route tests for admin-only API key management."""

from __future__ import annotations

from fastapi.testclient import TestClient

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


def add_admin_and_provider_tokens(conn: FakeAuthConnection) -> tuple[dict, dict]:
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
    return admin, provider


def test_admin_can_create_api_key_and_raw_key_is_returned_once_without_hash() -> None:
    client, conn = build_client()
    add_admin_and_provider_tokens(conn)

    response = client.post(
        "/admin/api-keys",
        headers={"Authorization": "Bearer admin-token"},
        json={
            "name": "Local export client",
            "description": "Local CSV export testing",
            "scopes": ["export:read"],
            "expires_in_days": 30,
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["api_key"].startswith("part3_")
    assert payload["key_prefix"] != payload["api_key"]
    assert payload["scopes"] == ["export:read"]
    assert "key_hash" not in response.text
    assert payload["api_key"] not in conn.api_keys_by_hash

    list_response = client.get("/admin/api-keys", headers={"Authorization": "Bearer admin-token"})
    assert list_response.status_code == 200
    assert "api_key" not in list_response.text
    assert "key_hash" not in list_response.text


def test_admin_api_key_creation_rejects_invalid_scope() -> None:
    client, conn = build_client()
    add_admin_and_provider_tokens(conn)

    response = client.post(
        "/admin/api-keys",
        headers={"Authorization": "Bearer admin-token"},
        json={"name": "Bad scope", "scopes": ["admin:all"]},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_provider_and_missing_or_invalid_user_tokens_cannot_manage_api_keys() -> None:
    client, conn = build_client()
    add_admin_and_provider_tokens(conn)

    missing = client.post("/admin/api-keys", json={"name": "Missing", "scopes": ["export:read"]})
    invalid = client.post(
        "/admin/api-keys",
        headers={"Authorization": "Bearer wrong"},
        json={"name": "Invalid", "scopes": ["export:read"]},
    )
    provider = client.post(
        "/admin/api-keys",
        headers={"Authorization": "Bearer provider-token", REQUEST_ID_HEADER: "provider-key-123"},
        json={"name": "Provider", "scopes": ["export:read"]},
    )

    assert missing.status_code == 401
    assert invalid.status_code == 401
    assert provider.status_code == 403
    assert provider.headers[REQUEST_ID_HEADER] == "provider-key-123"
    assert provider.json()["error"]["code"] == "forbidden"


def test_admin_can_list_and_revoke_api_key_without_exposing_secrets() -> None:
    client, conn = build_client()
    admin, _ = add_admin_and_provider_tokens(conn)
    raw_key = "part3_to_revoke_secret_value"
    api_key = conn.add_api_key(raw_api_key=raw_key, scopes=["export:read"], created_by_user_id=str(admin["id"]))

    list_response = client.get("/admin/api-keys", headers={"Authorization": "Bearer admin-token"})
    assert list_response.status_code == 200
    assert list_response.json()[0]["id"] == api_key["id"]
    assert raw_key not in list_response.text
    assert "key_hash" not in list_response.text

    revoke_response = client.post(f"/admin/api-keys/{api_key['id']}/revoke", headers={"Authorization": "Bearer admin-token"})
    assert revoke_response.status_code == 200
    assert revoke_response.json() == {"id": api_key["id"], "revoked": True}
    assert conn.api_keys_by_id[api_key["id"]]["is_active"] is False

    second_revoke = client.post(f"/admin/api-keys/{api_key['id']}/revoke", headers={"Authorization": "Bearer admin-token"})
    assert second_revoke.status_code == 200
    assert second_revoke.json()["revoked"] is True


def test_provider_cannot_revoke_and_missing_key_returns_404() -> None:
    client, conn = build_client()
    add_admin_and_provider_tokens(conn)

    provider = client.post(
        "/admin/api-keys/00000000-0000-0000-0000-000000000001/revoke",
        headers={"Authorization": "Bearer provider-token"},
    )
    missing = client.post(
        "/admin/api-keys/00000000-0000-0000-0000-000000000001/revoke",
        headers={"Authorization": "Bearer admin-token"},
    )

    assert provider.status_code == 403
    assert missing.status_code == 404
