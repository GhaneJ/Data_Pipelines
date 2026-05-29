"""Route tests for database-backed login, whoami, and logout."""

from __future__ import annotations

from datetime import timedelta

from fastapi.testclient import TestClient

from backend.app.dependencies import get_db_connection
from backend.app.main import create_app
from backend.app.auth.models import Role
from backend.app.auth.tokens import utc_now
from backend.tests.auth_test_utils import FakeAuthConnection, override_db

REQUEST_ID_HEADER = "X-Request-ID"


def build_client(conn: FakeAuthConnection) -> TestClient:
    app = create_app(run_startup_seeder=False)
    app.dependency_overrides[get_db_connection] = override_db(conn)
    return TestClient(app)


def assert_safe_auth_error(response, *, status_code: int, code: str, request_id: str) -> None:
    assert response.status_code == status_code
    assert response.headers[REQUEST_ID_HEADER] == request_id
    payload = response.json()
    assert payload["error"]["code"] == code
    assert payload["error"]["request_id"] == request_id
    assert payload["detail"] == payload["error"]["message"]


def test_login_valid_admin_credentials_return_bearer_token_without_sensitive_fields() -> None:
    conn = FakeAuthConnection()
    conn.add_user(username="admin", password="admin-password", role=Role.ADMIN, display_name="Local Admin")
    client = build_client(conn)

    response = client.post("/auth/login", json={"username": "admin", "password": "admin-password"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["access_token"]
    assert payload["token_type"] == "bearer"
    assert payload["expires_at"]
    assert "password" not in response.text
    assert "token_hash" not in response.text
    assert payload["access_token"] not in conn.tokens_by_hash


def test_login_valid_provider_credentials_return_bearer_token() -> None:
    conn = FakeAuthConnection()
    conn.add_user(
        username="provider",
        password="provider-password",
        role=Role.PROVIDER,
        display_name="Local Provider",
        provider_id="999999",
    )
    client = build_client(conn)

    response = client.post("/auth/login", json={"username": "provider", "password": "provider-password"})

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"


def test_login_invalid_username_or_password_returns_401_and_updates_failed_count() -> None:
    conn = FakeAuthConnection()
    user = conn.add_user(username="admin", password="admin-password", role=Role.ADMIN)
    client = build_client(conn)

    missing = client.post("/auth/login", json={"username": "missing", "password": "admin-password"})
    wrong = client.post("/auth/login", json={"username": "admin", "password": "wrong"})

    assert missing.status_code == 401
    assert wrong.status_code == 401
    assert user["failed_login_count"] == 1
    assert "admin-password" not in wrong.text
    assert "wrong" not in wrong.text


def test_inactive_or_locked_user_cannot_login() -> None:
    conn = FakeAuthConnection()
    conn.add_user(username="inactive", password="pw", role=Role.ADMIN, is_active=False)
    conn.add_user(username="locked", password="pw", role=Role.ADMIN, locked_until=utc_now() + timedelta(minutes=10))
    client = build_client(conn)

    inactive = client.post("/auth/login", json={"username": "inactive", "password": "pw"})
    locked = client.post("/auth/login", json={"username": "locked", "password": "pw"})

    assert inactive.status_code == 401
    assert locked.status_code == 401


def test_successful_login_clears_failed_login_count_and_lock_state() -> None:
    conn = FakeAuthConnection()
    user = conn.add_user(
        username="admin",
        password="admin-password",
        role=Role.ADMIN,
        failed_login_count=3,
        locked_until=utc_now() - timedelta(minutes=1),
    )
    client = build_client(conn)

    response = client.post("/auth/login", json={"username": "admin", "password": "admin-password"})

    assert response.status_code == 200
    assert user["failed_login_count"] == 0
    assert user["locked_until"] is None


def test_whoami_missing_malformed_invalid_expired_and_revoked_tokens_return_401() -> None:
    conn = FakeAuthConnection()
    conn.add_user(username="admin", password="admin-password", role=Role.ADMIN)
    conn.add_token(username="admin", raw_token="expired", expires_at=utc_now() - timedelta(minutes=1))
    conn.add_token(username="admin", raw_token="revoked", revoked=True)
    client = build_client(conn)

    missing = client.get("/auth/whoami", headers={REQUEST_ID_HEADER: "missing-123"})
    malformed = client.get("/auth/whoami", headers={REQUEST_ID_HEADER: "malformed-123", "Authorization": "Token bad"})
    invalid = client.get("/auth/whoami", headers={REQUEST_ID_HEADER: "invalid-123", "Authorization": "Bearer bad"})
    expired = client.get("/auth/whoami", headers={REQUEST_ID_HEADER: "expired-123", "Authorization": "Bearer expired"})
    revoked = client.get("/auth/whoami", headers={REQUEST_ID_HEADER: "revoked-123", "Authorization": "Bearer revoked"})

    assert_safe_auth_error(missing, status_code=401, code="unauthorized", request_id="missing-123")
    assert_safe_auth_error(malformed, status_code=401, code="unauthorized", request_id="malformed-123")
    assert_safe_auth_error(invalid, status_code=401, code="unauthorized", request_id="invalid-123")
    assert_safe_auth_error(expired, status_code=401, code="unauthorized", request_id="expired-123")
    assert_safe_auth_error(revoked, status_code=401, code="unauthorized", request_id="revoked-123")


def test_whoami_valid_admin_and_provider_tokens_return_safe_principals() -> None:
    conn = FakeAuthConnection()
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
    client = build_client(conn)

    admin_response = client.get("/auth/whoami", headers={"Authorization": "Bearer admin-token"})
    provider_response = client.get("/auth/whoami", headers={"Authorization": "Bearer provider-token"})

    assert admin_response.status_code == 200
    assert admin_response.json() == {
        "subject": f"user:{admin['id']}",
        "username": "admin",
        "display_name": "Local Admin",
        "role": "admin",
        "provider_id": None,
    }
    assert provider_response.status_code == 200
    assert provider_response.json() == {
        "subject": f"user:{provider['id']}",
        "username": "provider",
        "display_name": "Local Provider",
        "role": "provider",
        "provider_id": "999999",
    }
    assert "admin-token" not in admin_response.text
    assert "provider-token" not in provider_response.text


def test_logout_revokes_current_token_and_token_cannot_be_reused() -> None:
    conn = FakeAuthConnection()
    conn.add_user(username="admin", password="admin-password", role=Role.ADMIN)
    conn.add_token(username="admin", raw_token="admin-token")
    client = build_client(conn)

    logout_response = client.post("/auth/logout", headers={"Authorization": "Bearer admin-token"})
    whoami_response = client.get("/auth/whoami", headers={"Authorization": "Bearer admin-token"})

    assert logout_response.status_code == 200
    assert logout_response.json() == {"revoked": True}
    assert "admin-token" not in logout_response.text
    assert whoami_response.status_code == 401


def test_logout_without_token_returns_401() -> None:
    conn = FakeAuthConnection()
    client = build_client(conn)

    response = client.post("/auth/logout", headers={REQUEST_ID_HEADER: "logout-missing-123"})

    assert_safe_auth_error(response, status_code=401, code="unauthorized", request_id="logout-missing-123")
