"""Route tests for bearer-token authentication and safe auth responses."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.auth.token_store import ADMIN_TOKEN_ENV_VAR, PROVIDER_ID_ENV_VAR, PROVIDER_TOKEN_ENV_VAR
from backend.app.main import create_app

REQUEST_ID_HEADER = "X-Request-ID"


def build_client() -> TestClient:
    """Create a lightweight TestClient for auth route checks."""
    return TestClient(create_app(run_startup_seeder=False))


def assert_safe_auth_error(response, *, status_code: int, code: str, request_id: str) -> None:
    """Check the standardized 3.14+ error envelope used by auth failures."""
    assert response.status_code == status_code
    assert response.headers[REQUEST_ID_HEADER] == request_id
    payload = response.json()
    assert payload["error"]["code"] == code
    assert payload["error"]["request_id"] == request_id
    assert payload["detail"] == payload["error"]["message"]


def test_whoami_missing_bearer_token_returns_401_with_request_id(monkeypatch) -> None:
    """The auth inspection endpoint must not be public."""
    monkeypatch.setenv(ADMIN_TOKEN_ENV_VAR, "admin-secret")
    client = build_client()

    response = client.get("/auth/whoami", headers={REQUEST_ID_HEADER: "auth-missing-123"})

    assert_safe_auth_error(response, status_code=401, code="unauthorized", request_id="auth-missing-123")
    assert response.json()["detail"] == "Authentication is required."


def test_whoami_malformed_bearer_header_returns_401(monkeypatch) -> None:
    """Only Authorization: Bearer <token> should be accepted."""
    monkeypatch.setenv(ADMIN_TOKEN_ENV_VAR, "admin-secret")
    client = build_client()

    response = client.get(
        "/auth/whoami",
        headers={REQUEST_ID_HEADER: "auth-malformed-123", "Authorization": "Token admin-secret"},
    )

    assert_safe_auth_error(response, status_code=401, code="unauthorized", request_id="auth-malformed-123")
    assert "Bearer" in response.json()["detail"]


def test_whoami_invalid_bearer_token_returns_401(monkeypatch) -> None:
    """Unknown bearer tokens should be rejected without leaking configured tokens."""
    monkeypatch.setenv(ADMIN_TOKEN_ENV_VAR, "admin-secret")
    client = build_client()

    response = client.get(
        "/auth/whoami",
        headers={REQUEST_ID_HEADER: "auth-invalid-123", "Authorization": "Bearer wrong-secret"},
    )

    assert_safe_auth_error(response, status_code=401, code="unauthorized", request_id="auth-invalid-123")
    assert "admin-secret" not in response.text
    assert "wrong-secret" not in response.text


def test_whoami_valid_admin_bearer_token_returns_principal_without_token(monkeypatch) -> None:
    """The admin bearer token should map to a safe admin principal."""
    monkeypatch.setenv(ADMIN_TOKEN_ENV_VAR, "admin-secret")
    client = build_client()

    response = client.get("/auth/whoami", headers={"Authorization": "Bearer admin-secret"})

    assert response.status_code == 200
    assert response.json() == {"subject": "local-admin", "role": "admin", "provider_id": None}
    assert "admin-secret" not in response.text
    assert REQUEST_ID_HEADER in response.headers


def test_whoami_valid_provider_bearer_token_returns_principal_without_token(monkeypatch) -> None:
    """The provider bearer token should map to a provider principal when configured."""
    monkeypatch.setenv(ADMIN_TOKEN_ENV_VAR, "admin-secret")
    monkeypatch.setenv(PROVIDER_TOKEN_ENV_VAR, "provider-secret")
    monkeypatch.setenv(PROVIDER_ID_ENV_VAR, "999999")
    client = build_client()

    response = client.get("/auth/whoami", headers={"Authorization": "Bearer provider-secret"})

    assert response.status_code == 200
    assert response.json() == {"subject": "local-provider", "role": "provider", "provider_id": "999999"}
    assert "provider-secret" not in response.text
    assert REQUEST_ID_HEADER in response.headers
