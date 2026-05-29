"""Database repository helpers for authentication and authorization."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

import psycopg

from backend.app.auth.models import AuthenticatedPrincipal, Role
from backend.app.auth.password_hashing import PasswordHashConfig


AuthConnection = psycopg.Connection[dict[str, Any]]

USER_SAFE_COLUMNS = """
    id,
    username,
    display_name,
    role,
    provider_id,
    password_hash,
    password_salt,
    password_algorithm,
    password_iterations,
    is_active,
    failed_login_count,
    locked_until,
    last_login_at,
    password_changed_at,
    created_at,
    updated_at
"""

TOKEN_JOIN_COLUMNS = """
    t.id AS token_id,
    t.user_id,
    t.expires_at,
    t.revoked_at,
    t.last_used_at,
    u.id AS id,
    u.username,
    u.display_name,
    u.role,
    u.provider_id,
    u.password_hash,
    u.password_salt,
    u.password_algorithm,
    u.password_iterations,
    u.is_active,
    u.failed_login_count,
    u.locked_until,
    u.last_login_at,
    u.password_changed_at,
    u.created_at,
    u.updated_at
"""


def normalize_username(username: str) -> str:
    """Normalize usernames for lookup and bootstrap idempotency."""
    return username.strip().lower()


def principal_from_user_row(row: dict[str, Any]) -> AuthenticatedPrincipal:
    """Build a safe principal from an auth_users row."""
    return AuthenticatedPrincipal(
        subject=f"user:{row['id']}",
        username=row["username"],
        display_name=row["display_name"],
        role=Role(row["role"]),
        provider_id=row.get("provider_id"),
    )


def find_user_by_username(conn: AuthConnection, username: str) -> dict[str, Any] | None:
    """Return one auth user by normalized username, if it exists."""
    with conn.cursor() as cursor:
        cursor.execute(
            f"SELECT {USER_SAFE_COLUMNS} FROM auth_users WHERE username = %(username)s;",
            {"username": normalize_username(username)},
        )
        return cursor.fetchone()


def find_user_by_id(conn: AuthConnection, user_id: str) -> dict[str, Any] | None:
    """Return one auth user by id, if it exists."""
    with conn.cursor() as cursor:
        cursor.execute(f"SELECT {USER_SAFE_COLUMNS} FROM auth_users WHERE id = %(user_id)s;", {"user_id": user_id})
        return cursor.fetchone()


def create_bootstrap_user(
    conn: AuthConnection,
    *,
    username: str,
    display_name: str,
    role: Role,
    provider_id: str | None,
    password_config: PasswordHashConfig,
) -> dict[str, Any]:
    """Create one bootstrap user and return its row.

    Existing users are intentionally not overwritten by this function. Callers
    should check for existence first so bootstrap behavior stays explicit.
    """
    user_id = str(uuid4())
    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            INSERT INTO auth_users (
                id,
                username,
                display_name,
                role,
                provider_id,
                password_hash,
                password_salt,
                password_algorithm,
                password_iterations
            )
            VALUES (
                %(id)s,
                %(username)s,
                %(display_name)s,
                %(role)s,
                %(provider_id)s,
                %(password_hash)s,
                %(password_salt)s,
                %(password_algorithm)s,
                %(password_iterations)s
            )
            RETURNING {USER_SAFE_COLUMNS};
            """,
            {
                "id": user_id,
                "username": normalize_username(username),
                "display_name": display_name.strip(),
                "role": role.value,
                "provider_id": provider_id.strip() if provider_id else None,
                "password_hash": password_config.password_hash,
                "password_salt": password_config.password_salt,
                "password_algorithm": password_config.password_algorithm,
                "password_iterations": password_config.password_iterations,
            },
        )
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError("Bootstrap user insertion did not return a row.")
        return row


def increment_failed_login_count(
    conn: AuthConnection,
    *,
    user_id: str,
    lock_threshold: int,
    locked_until: datetime | None,
) -> None:
    """Increment failed logins and optionally lock the user temporarily."""
    with conn.cursor() as cursor:
        if locked_until is None:
            cursor.execute(
                """
                UPDATE auth_users
                SET failed_login_count = failed_login_count + 1,
                    updated_at = NOW()
                WHERE id = %(user_id)s;
                """,
                {"user_id": user_id},
            )
            return

        cursor.execute(
            """
            UPDATE auth_users
            SET failed_login_count = failed_login_count + 1,
                locked_until = CASE
                    WHEN failed_login_count + 1 >= %(lock_threshold)s THEN %(locked_until)s
                    ELSE locked_until
                END,
                updated_at = NOW()
            WHERE id = %(user_id)s;
            """,
            {"user_id": user_id, "lock_threshold": lock_threshold, "locked_until": locked_until},
        )


def clear_failed_login_state(conn: AuthConnection, *, user_id: str) -> None:
    """Clear failed login count and temporary lock after a successful login."""
    with conn.cursor() as cursor:
        cursor.execute(
            """
            UPDATE auth_users
            SET failed_login_count = 0,
                locked_until = NULL,
                last_login_at = NOW(),
                updated_at = NOW()
            WHERE id = %(user_id)s;
            """,
            {"user_id": user_id},
        )


def create_access_token_record(
    conn: AuthConnection,
    *,
    user_id: str,
    token_hash: str,
    expires_at: datetime,
) -> dict[str, Any]:
    """Persist an access-token hash and return safe token metadata."""
    token_id = str(uuid4())
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO auth_access_tokens (id, user_id, token_hash, expires_at)
            VALUES (%(id)s, %(user_id)s, %(token_hash)s, %(expires_at)s)
            RETURNING id, user_id, created_at, expires_at, revoked_at, last_used_at;
            """,
            {"id": token_id, "user_id": user_id, "token_hash": token_hash, "expires_at": expires_at},
        )
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError("Access-token insertion did not return a row.")
        return row


def resolve_access_token_hash(conn: AuthConnection, *, token_hash: str) -> dict[str, Any] | None:
    """Return joined token/user data for one token hash."""
    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT {TOKEN_JOIN_COLUMNS}
            FROM auth_access_tokens t
            JOIN auth_users u ON u.id = t.user_id
            WHERE t.token_hash = %(token_hash)s;
            """,
            {"token_hash": token_hash},
        )
        return cursor.fetchone()


def update_token_last_used(conn: AuthConnection, *, token_id: str) -> None:
    """Record that an active token was used successfully."""
    with conn.cursor() as cursor:
        cursor.execute(
            "UPDATE auth_access_tokens SET last_used_at = NOW() WHERE id = %(token_id)s;",
            {"token_id": token_id},
        )


def revoke_access_token_hash(conn: AuthConnection, *, token_hash: str) -> bool:
    """Revoke one active token by hash and report whether it changed."""
    with conn.cursor() as cursor:
        cursor.execute(
            """
            UPDATE auth_access_tokens
            SET revoked_at = NOW()
            WHERE token_hash = %(token_hash)s
              AND revoked_at IS NULL
            RETURNING id;
            """,
            {"token_hash": token_hash},
        )
        return cursor.fetchone() is not None


def revoke_all_access_tokens_for_user(conn: AuthConnection, *, user_id: str) -> int:
    """Revoke all active tokens for a user and return the affected count."""
    with conn.cursor() as cursor:
        cursor.execute(
            """
            UPDATE auth_access_tokens
            SET revoked_at = NOW()
            WHERE user_id = %(user_id)s
              AND revoked_at IS NULL;
            """,
            {"user_id": user_id},
        )
        return int(cursor.rowcount or 0)
