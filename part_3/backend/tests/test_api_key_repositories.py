"""Repository tests for database-backed API keys."""

from __future__ import annotations

from datetime import timedelta

from backend.app.api_keys.key_utils import extract_key_prefix, generate_api_key, hash_api_key
from backend.app.api_keys.repositories import (
    create_api_key_record,
    deserialize_scopes,
    list_api_key_records,
    resolve_active_api_key_hash,
    revoke_api_key_record,
    serialize_scopes,
    update_api_key_last_used,
)
from backend.app.auth.models import Role
from backend.app.auth.tokens import utc_now
from backend.tests.auth_test_utils import FakeAuthConnection


def test_scope_serialization_is_simple_and_explainable() -> None:
    assert serialize_scopes(["export:read", "export:read", "stats:read"]) == "export:read,stats:read"
    assert deserialize_scopes("export:read, stats:read") == ["export:read", "stats:read"]


def test_create_resolve_list_and_revoke_api_key_record() -> None:
    conn = FakeAuthConnection()
    admin = conn.add_user(username="admin", password="admin-password", role=Role.ADMIN)
    raw_key = generate_api_key()
    key_hash = hash_api_key(raw_key)

    created = create_api_key_record(
        conn,
        name="Local export client",
        description="Local CSV export testing",
        key_prefix=extract_key_prefix(raw_key),
        key_hash=key_hash,
        scopes=["export:read"],
        expires_at=utc_now() + timedelta(days=30),
        created_by_user_id=str(admin["id"]),
    )

    assert created["name"] == "Local export client"
    assert created["scopes"] == ["export:read"]
    assert "key_hash" not in created
    assert raw_key not in str(conn.api_keys_by_hash)
    assert conn.api_keys_by_hash[key_hash]["key_hash"] == key_hash
    assert conn.api_keys_by_hash[key_hash]["key_hash"] != raw_key

    resolved = resolve_active_api_key_hash(conn, key_hash=key_hash)
    assert resolved is not None
    assert resolved["id"] == created["id"]
    assert "key_hash" not in resolved

    update_api_key_last_used(conn, key_id=str(created["id"]))
    assert conn.api_keys_by_hash[key_hash]["last_used_at"] is not None

    listed = list_api_key_records(conn)
    assert len(listed) == 1
    assert "key_hash" not in listed[0]

    revoked = revoke_api_key_record(conn, key_id=str(created["id"]), revoked_by_user_id=str(admin["id"]))
    assert revoked is not None
    assert revoked["is_active"] is False
    assert resolve_active_api_key_hash(conn, key_hash=key_hash) is None


def test_invalid_expired_and_revoked_keys_fail_resolution() -> None:
    conn = FakeAuthConnection()
    conn.add_api_key(raw_api_key="part3_valid", scopes=["export:read"])
    conn.add_api_key(raw_api_key="part3_expired", scopes=["export:read"], expires_at=utc_now() - timedelta(minutes=1))
    conn.add_api_key(raw_api_key="part3_revoked", scopes=["export:read"], revoked=True)
    conn.add_api_key(raw_api_key="part3_inactive", scopes=["export:read"], is_active=False)

    assert resolve_active_api_key_hash(conn, key_hash=hash_api_key("part3_valid")) is not None
    assert resolve_active_api_key_hash(conn, key_hash=hash_api_key("does-not-exist")) is None
    assert resolve_active_api_key_hash(conn, key_hash=hash_api_key("part3_expired")) is None
    assert resolve_active_api_key_hash(conn, key_hash=hash_api_key("part3_revoked")) is None
    assert resolve_active_api_key_hash(conn, key_hash=hash_api_key("part3_inactive")) is None


def test_api_key_schema_can_be_added_without_resetting_curated_tables() -> None:
    from backend.app.services import database_seeder

    schema_sql = database_seeder.read_sql_file(database_seeder.SCHEMA_PATH)
    indexes_sql = database_seeder.read_sql_file(database_seeder.INDEXES_PATH)
    reset_sql = database_seeder.read_sql_file(database_seeder.SQL_ROOT / "reset_schema.sql")

    assert "CREATE TABLE IF NOT EXISTS api_keys" in schema_sql
    assert "CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash" in indexes_sql
    assert "DROP TABLE IF EXISTS api_keys" not in reset_sql
