"""Route tests for protecting CSV export with scoped API keys."""

from __future__ import annotations

from datetime import timedelta

from fastapi.testclient import TestClient

from backend.app.auth.models import Role
from backend.app.auth.tokens import utc_now
from backend.app.dependencies import get_db_connection
from backend.app.main import create_app
from backend.app.routers import export as export_router
from backend.tests.auth_test_utils import FakeAuthConnection, override_db

REQUEST_ID_HEADER = "X-Request-ID"


def build_client(conn: FakeAuthConnection | None = None) -> tuple[TestClient, FakeAuthConnection]:
    fake_conn = conn or FakeAuthConnection()
    app = create_app(run_startup_seeder=False)
    app.dependency_overrides[get_db_connection] = override_db(fake_conn)
    return TestClient(app), fake_conn


def test_export_without_api_key_or_with_invalid_api_key_returns_401() -> None:
    client, conn = build_client()
    conn.add_api_key(raw_api_key="part3_valid", scopes=["export:read"])

    missing = client.get("/export/applications?year=2024", headers={REQUEST_ID_HEADER: "missing-api-key-123"})
    malformed = client.get("/export/applications?year=2024", headers={"X-API-Key": "part3_one two"})
    invalid = client.get("/export/applications?year=2024", headers={"X-API-Key": "part3_wrong"})

    assert missing.status_code == 401
    assert missing.headers[REQUEST_ID_HEADER] == "missing-api-key-123"
    assert missing.json()["error"]["code"] == "unauthorized"
    assert malformed.status_code == 401
    assert invalid.status_code == 401


def test_export_with_expired_or_revoked_api_key_returns_401() -> None:
    client, conn = build_client()
    conn.add_api_key(raw_api_key="part3_expired", scopes=["export:read"], expires_at=utc_now() - timedelta(minutes=1))
    conn.add_api_key(raw_api_key="part3_revoked", scopes=["export:read"], revoked=True)

    expired = client.get("/export/applications?year=2024", headers={"X-API-Key": "part3_expired"})
    revoked = client.get("/export/applications?year=2024", headers={"X-API-Key": "part3_revoked"})

    assert expired.status_code == 401
    assert revoked.status_code == 401


def test_export_with_valid_key_missing_export_scope_returns_403() -> None:
    client, conn = build_client()
    conn.add_api_key(raw_api_key="part3_stats_only", scopes=["stats:read"])

    response = client.get("/export/applications?year=2024", headers={"X-API-Key": "part3_stats_only"})

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_export_with_valid_export_scope_returns_csv_and_preserves_filters(monkeypatch) -> None:
    captured = {}

    def fake_fetch(conn, *, filters, limit=None):
        captured["filters"] = filters
        captured["limit"] = limit
        return [
            {
                "diarienummer": "MYH 2024/1",
                "source_year": 2024,
                "utbildningsnamn": "Data Engineer",
                "utbildningsomrade": "Data/IT",
                "beslut": "Beviljad",
                "beslut_normalized": "approved",
                "is_approved": True,
                "lan": "Stockholms län",
                "kommun": "Stockholm",
                "yh_poang": 400,
                "studieform": "Distans",
                "studietakt_procent": 100,
                "utbildningsanordnare": "Example Provider",
                "huvudmannatyp": "Privat",
                "huvudmannatyp_normalized": "private",
                "sokta_utbildningsomgangar": 1,
                "beviljade_utbildningsomgangar": 1,
                "sokta_platser_totalt": 30,
                "beviljade_platser_totalt": 30,
            }
        ]

    monkeypatch.setattr(export_router, "fetch_export_applications", fake_fetch)
    client, conn = build_client()
    key = conn.add_api_key(raw_api_key="part3_export", scopes=["export:read"])

    response = client.get(
        "/export/applications?year=2024&decision=approved&limit=10",
        headers={"X-API-Key": "part3_export", REQUEST_ID_HEADER: "export-ok-123"},
    )

    assert response.status_code == 200
    assert response.headers[REQUEST_ID_HEADER] == "export-ok-123"
    assert response.headers["content-type"].startswith("text/csv")
    assert "diarienummer,source_year" in response.text
    assert "MYH 2024/1" in response.text
    assert captured["filters"].source_year == 2024
    assert captured["filters"].decision == "approved"
    assert captured["limit"] == 10
    assert conn.api_keys_by_id[key["id"]]["last_used_at"] is not None


def test_export_empty_result_still_returns_header(monkeypatch) -> None:
    monkeypatch.setattr(export_router, "fetch_export_applications", lambda conn, *, filters, limit=None: [])
    client, conn = build_client()
    conn.add_api_key(raw_api_key="part3_export", scopes=["export:read"])

    response = client.get("/export/applications?year=1999", headers={"X-API-Key": "part3_export"})

    # year=1999 is rejected by query validation before reaching CSV logic.
    assert response.status_code == 422

    ok = client.get("/export/applications?year=2024", headers={"X-API-Key": "part3_export"})
    assert ok.status_code == 200
    assert ok.text.startswith("diarienummer,source_year")


def test_user_bearer_token_alone_does_not_satisfy_export_api_key_requirement() -> None:
    client, conn = build_client()
    conn.add_user(username="admin", password="admin-password", role=Role.ADMIN)
    conn.add_token(username="admin", raw_token="admin-token")

    response = client.get("/export/applications?year=2024", headers={"Authorization": "Bearer admin-token"})

    assert response.status_code == 401


def test_public_read_stats_and_provider_endpoints_remain_public_without_api_key(monkeypatch) -> None:
    from backend.app.routers import applications, providers, stats

    monkeypatch.setattr(applications, "fetch_applications", lambda conn, filters, limit, offset: {"items": [], "total": 0, "limit": limit, "offset": offset})
    monkeypatch.setattr(stats, "fetch_stats_by_year", lambda conn: [])
    monkeypatch.setattr(providers, "fetch_providers", lambda conn, search, limit, offset: {"items": [], "total": 0, "limit": limit, "offset": offset})
    client, _ = build_client()

    applications_response = client.get("/applications?limit=5")
    stats_response = client.get("/stats/by-year")
    providers_response = client.get("/providers?limit=5")

    assert applications_response.status_code == 200
    assert stats_response.status_code == 200
    assert providers_response.status_code == 200
