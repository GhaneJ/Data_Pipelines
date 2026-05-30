"""Regression checks around provider submissions, auth, API keys, and public routes."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.auth.models import Role
from backend.app.dependencies import get_db_connection
from backend.app.main import create_app
from backend.tests.auth_test_utils import FakeAuthConnection, override_db


def build_client() -> tuple[TestClient, FakeAuthConnection]:
    conn = FakeAuthConnection()
    app = create_app(run_startup_seeder=False)
    app.dependency_overrides[get_db_connection] = override_db(conn)
    return TestClient(app), conn


def seed_auth(conn: FakeAuthConnection) -> None:
    admin = conn.add_user(username="admin", password="admin-password", role=Role.ADMIN, display_name="Local Admin")
    conn.add_user(
        username="provider",
        password="provider-password",
        role=Role.PROVIDER,
        display_name="Local Provider",
        provider_id="999999",
    )
    conn.add_token(username="admin", raw_token="admin-token")
    conn.add_token(username="provider", raw_token="provider-token")
    conn.add_api_key(raw_api_key="part3_export_secret_value", scopes=["export:read"], created_by_user_id=admin["id"])


def test_openapi_keeps_public_export_admin_and_provider_boundaries_registered() -> None:
    client, _ = build_client()

    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/applications" in paths
    assert "/stats/by-year" in paths
    assert "/providers" in paths
    assert "/export/applications" in paths
    assert "/admin/api-keys" in paths
    assert "/provider/submissions" in paths
    assert "/provider/submissions/{submission_id}/submit" in paths


def test_x_admin_token_and_api_key_do_not_grant_provider_submission_access() -> None:
    client, conn = build_client()
    seed_auth(conn)

    x_admin_token = client.get("/provider/submissions", headers={"X-Admin-Token": "legacy-admin-token"})
    api_key = client.get("/provider/submissions", headers={"X-API-Key": "part3_export_secret_value"})
    admin_bearer = client.get("/provider/submissions", headers={"Authorization": "Bearer admin-token"})
    provider_bearer = client.get("/provider/submissions", headers={"Authorization": "Bearer provider-token"})

    assert x_admin_token.status_code == 401
    assert api_key.status_code == 401
    assert admin_bearer.status_code == 403
    assert provider_bearer.status_code == 200


def test_provider_bearer_does_not_satisfy_export_api_key_protection() -> None:
    client, conn = build_client()
    seed_auth(conn)

    bearer_only = client.get("/export/applications?year=2024", headers={"Authorization": "Bearer provider-token"})

    assert bearer_only.status_code == 401
    assert bearer_only.json()["error"]["code"] == "unauthorized"
