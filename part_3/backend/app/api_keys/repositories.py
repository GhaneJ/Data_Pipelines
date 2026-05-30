"""Repository helpers for database-backed API keys."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

import psycopg

ApiKeyConnection = psycopg.Connection[dict[str, Any]]
SCOPE_SEPARATOR = ","

API_KEY_SAFE_COLUMNS = """
    id,
    name,
    description,
    key_prefix,
    scopes,
    is_active,
    expires_at,
    revoked_at,
    revoked_by_user_id,
    created_by_user_id,
    created_at,
    updated_at,
    last_used_at
"""


def serialize_scopes(scopes: list[str]) -> str:
    """Serialize scopes to a simple comma-separated text field."""
    cleaned: list[str] = []
    for scope in scopes:
        normalized = scope.strip().lower()
        if normalized and normalized not in cleaned:
            cleaned.append(normalized)
    return SCOPE_SEPARATOR.join(cleaned)


def deserialize_scopes(value: str | None) -> list[str]:
    """Deserialize comma-separated scope text from the database."""
    if not value:
        return []
    return [scope for scope in (part.strip().lower() for part in value.split(SCOPE_SEPARATOR)) if scope]


def api_key_row_to_safe_dict(row: dict[str, Any]) -> dict[str, Any]:
    """Convert an API key row into a safe response/principal dictionary."""
    safe = {key: value for key, value in row.items() if key not in {"key_hash"}}
    safe["id"] = str(safe["id"])
    safe["created_by_user_id"] = str(safe["created_by_user_id"])
    if safe.get("revoked_by_user_id") is not None:
        safe["revoked_by_user_id"] = str(safe["revoked_by_user_id"])
    safe["scopes"] = deserialize_scopes(str(row.get("scopes") or ""))
    return safe


def create_api_key_record(
    conn: ApiKeyConnection,
    *,
    name: str,
    description: str | None,
    key_prefix: str,
    key_hash: str,
    scopes: list[str],
    expires_at: datetime | None,
    created_by_user_id: str,
) -> dict[str, Any]:
    """Insert one hashed API key row and return safe metadata."""
    key_id = str(uuid4())
    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            INSERT INTO api_keys (
                id,
                name,
                description,
                key_prefix,
                key_hash,
                scopes,
                expires_at,
                created_by_user_id
            )
            VALUES (
                %(id)s,
                %(name)s,
                %(description)s,
                %(key_prefix)s,
                %(key_hash)s,
                %(scopes)s,
                %(expires_at)s,
                %(created_by_user_id)s
            )
            RETURNING {API_KEY_SAFE_COLUMNS};
            """,
            {
                "id": key_id,
                "name": name,
                "description": description,
                "key_prefix": key_prefix,
                "key_hash": key_hash,
                "scopes": serialize_scopes(scopes),
                "expires_at": expires_at,
                "created_by_user_id": created_by_user_id,
            },
        )
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError("API key insertion did not return a row.")
        return api_key_row_to_safe_dict(row)


def list_api_key_records(conn: ApiKeyConnection) -> list[dict[str, Any]]:
    """Return safe metadata for all API keys, newest first."""
    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT {API_KEY_SAFE_COLUMNS}
            FROM api_keys
            ORDER BY created_at DESC, name ASC;
            """
        )
        return [api_key_row_to_safe_dict(row) for row in cursor.fetchall()]


def resolve_active_api_key_hash(conn: ApiKeyConnection, *, key_hash: str) -> dict[str, Any] | None:
    """Return one active, unexpired, non-revoked API key by hash, if valid."""
    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT {API_KEY_SAFE_COLUMNS}
            FROM api_keys
            WHERE key_hash = %(key_hash)s
              AND is_active = TRUE
              AND revoked_at IS NULL
              AND (expires_at IS NULL OR expires_at > NOW());
            """,
            {"key_hash": key_hash},
        )
        row = cursor.fetchone()
        return api_key_row_to_safe_dict(row) if row is not None else None


def update_api_key_last_used(conn: ApiKeyConnection, *, key_id: str) -> None:
    """Record successful use of an API key."""
    with conn.cursor() as cursor:
        cursor.execute(
            """
            UPDATE api_keys
            SET last_used_at = NOW(),
                updated_at = NOW()
            WHERE id = %(key_id)s;
            """,
            {"key_id": key_id},
        )


def revoke_api_key_record(
    conn: ApiKeyConnection,
    *,
    key_id: str,
    revoked_by_user_id: str,
) -> dict[str, Any] | None:
    """Revoke one API key idempotently and return safe metadata."""
    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            UPDATE api_keys
            SET is_active = FALSE,
                revoked_at = COALESCE(revoked_at, NOW()),
                revoked_by_user_id = COALESCE(revoked_by_user_id, %(revoked_by_user_id)s),
                updated_at = NOW()
            WHERE id = %(key_id)s
            RETURNING {API_KEY_SAFE_COLUMNS};
            """,
            {"key_id": key_id, "revoked_by_user_id": revoked_by_user_id},
        )
        row = cursor.fetchone()
        return api_key_row_to_safe_dict(row) if row is not None else None
