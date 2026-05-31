"""Repository helpers for controlled signup and admin user management."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import psycopg

from backend.app.auth.models import Role
from backend.app.auth.password_hashing import PasswordHashConfig, hash_password
from backend.app.auth.repositories import USER_SAFE_COLUMNS, find_user_by_username, normalize_username
from backend.app.user_management.models import (
    ManagedUserCreateRequest,
    ManagedUserUpdateRequest,
    PasswordResetRequest,
    RegistrationRequestCreateRequest,
    RegistrationRequestReviewRequest,
    RegistrationRequestStatus,
)

ManagementConnection = psycopg.Connection[dict[str, Any]]

SAFE_USER_RETURNING = f"""
    {USER_SAFE_COLUMNS}
"""

SAFE_REGISTRATION_COLUMNS = """
    id,
    requested_username,
    display_name,
    email,
    provider_id,
    requested_role,
    organization_name,
    message,
    status,
    created_at,
    reviewed_by_user_id,
    reviewed_at,
    review_notes,
    created_user_id
"""

SAFE_SESSION_COLUMNS = """
    id,
    user_id,
    created_at,
    expires_at,
    revoked_at,
    last_used_at,
    (revoked_at IS NULL AND expires_at > NOW()) AS is_active
"""


class UserManagementConflictError(ValueError):
    """Raised when a user-management request conflicts with existing state."""


class UserManagementValidationError(ValueError):
    """Raised when safe business validation fails."""


class UserManagementStateError(ValueError):
    """Raised when a workflow transition is unavailable."""


def _user_id_from_subject(subject: str) -> str:
    return subject.removeprefix("user:")


def provider_exists(conn: ManagementConnection, provider_id: str) -> bool:
    """Return whether the curated provider id exists."""
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT 1 FROM providers WHERE provider_id::TEXT = %(provider_id)s;",
            {"provider_id": provider_id.strip()},
        )
        return cursor.fetchone() is not None


def _validate_provider_id(conn: ManagementConnection, provider_id: str | None, *, role: Role) -> str | None:
    if role == Role.ADMIN:
        if provider_id:
            raise UserManagementValidationError("Admin users must not be assigned a provider_id.")
        return None
    if role == Role.PROVIDER:
        cleaned = (provider_id or "").strip()
        if not cleaned:
            raise UserManagementValidationError("Provider users require provider_id.")
        if not provider_exists(conn, cleaned):
            raise UserManagementValidationError(f"Provider id {cleaned!r} was not found in the curated provider table.")
        return cleaned
    raise UserManagementValidationError("Unsupported role.")


def _insert_admin_event(
    conn: ManagementConnection,
    *,
    actor_user_id: str | None,
    action: str,
    target_user_id: str | None = None,
    registration_request_id: str | None = None,
    notes: str | None = None,
) -> None:
    """Write a small safe admin/auth event when the table is available."""
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO auth_admin_events (id, actor_user_id, target_user_id, registration_request_id, action, notes)
            VALUES (%(id)s, %(actor_user_id)s, %(target_user_id)s, %(registration_request_id)s, %(action)s, %(notes)s);
            """,
            {
                "id": str(uuid4()),
                "actor_user_id": actor_user_id,
                "target_user_id": target_user_id,
                "registration_request_id": registration_request_id,
                "action": action,
                "notes": notes,
            },
        )


def username_has_pending_request(conn: ManagementConnection, username: str) -> bool:
    """Return whether a pending registration request already uses username."""
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT 1
            FROM user_registration_requests
            WHERE requested_username = %(username)s
              AND status = 'pending';
            """,
            {"username": normalize_username(username)},
        )
        return cursor.fetchone() is not None


def create_registration_request(
    conn: ManagementConnection,
    *,
    payload: RegistrationRequestCreateRequest,
) -> dict[str, Any]:
    """Create a pending provider access request without creating a user."""
    username = normalize_username(payload.requested_username)
    if find_user_by_username(conn, username) is not None:
        raise UserManagementConflictError("Username is already used by an active user.")
    if username_has_pending_request(conn, username):
        raise UserManagementConflictError("A pending provider access request already exists for this username.")
    provider_id = _validate_provider_id(conn, payload.provider_id, role=Role.PROVIDER)
    password_config = hash_password(payload.password)
    request_id = str(uuid4())

    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            INSERT INTO user_registration_requests (
                id,
                requested_username,
                display_name,
                email,
                provider_id,
                requested_role,
                organization_name,
                message,
                pending_password_hash,
                pending_password_salt,
                pending_password_algorithm,
                pending_password_iterations
            )
            VALUES (
                %(id)s,
                %(requested_username)s,
                %(display_name)s,
                %(email)s,
                %(provider_id)s,
                'provider',
                %(organization_name)s,
                %(message)s,
                %(pending_password_hash)s,
                %(pending_password_salt)s,
                %(pending_password_algorithm)s,
                %(pending_password_iterations)s
            )
            RETURNING {SAFE_REGISTRATION_COLUMNS};
            """,
            {
                "id": request_id,
                "requested_username": username,
                "display_name": payload.display_name.strip(),
                "email": payload.email.strip() if payload.email else None,
                "provider_id": provider_id,
                "organization_name": payload.organization_name,
                "message": payload.message,
                "pending_password_hash": password_config.password_hash,
                "pending_password_salt": password_config.password_salt,
                "pending_password_algorithm": password_config.password_algorithm,
                "pending_password_iterations": password_config.password_iterations,
            },
        )
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError("Registration request insertion did not return a row.")

    _insert_admin_event(
        conn,
        actor_user_id=None,
        registration_request_id=request_id,
        action="registration_request_created",
        notes="Provider access request submitted.",
    )
    return row


def list_registration_requests(
    conn: ManagementConnection,
    *,
    status: RegistrationRequestStatus | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """List registration requests for admins."""
    where_clause = "WHERE status = %(status)s" if status else ""
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if status:
        params["status"] = status.value if isinstance(status, RegistrationRequestStatus) else str(status)
    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT {SAFE_REGISTRATION_COLUMNS}
            FROM user_registration_requests
            {where_clause}
            ORDER BY created_at DESC, requested_username ASC
            LIMIT %(limit)s OFFSET %(offset)s;
            """,
            params,
        )
        return cursor.fetchall()


def get_registration_request(conn: ManagementConnection, request_id: str) -> dict[str, Any] | None:
    """Return one safe registration request by id."""
    with conn.cursor() as cursor:
        cursor.execute(
            f"SELECT {SAFE_REGISTRATION_COLUMNS} FROM user_registration_requests WHERE id = %(id)s;",
            {"id": request_id},
        )
        return cursor.fetchone()


def _get_registration_request_with_secret(conn: ManagementConnection, request_id: str) -> dict[str, Any] | None:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                id,
                requested_username,
                display_name,
                email,
                provider_id,
                requested_role,
                organization_name,
                message,
                status,
                pending_password_hash,
                pending_password_salt,
                pending_password_algorithm,
                pending_password_iterations,
                created_at,
                reviewed_by_user_id,
                reviewed_at,
                review_notes,
                created_user_id
            FROM user_registration_requests
            WHERE id = %(id)s;
            """,
            {"id": request_id},
        )
        return cursor.fetchone()


def _insert_user(
    conn: ManagementConnection,
    *,
    username: str,
    display_name: str,
    role: Role,
    provider_id: str | None,
    password_config: PasswordHashConfig,
    is_active: bool = True,
) -> dict[str, Any]:
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
                password_iterations,
                is_active
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
                %(password_iterations)s,
                %(is_active)s
            )
            RETURNING {SAFE_USER_RETURNING};
            """,
            {
                "id": user_id,
                "username": normalize_username(username),
                "display_name": display_name.strip(),
                "role": role.value,
                "provider_id": provider_id,
                "password_hash": password_config.password_hash,
                "password_salt": password_config.password_salt,
                "password_algorithm": password_config.password_algorithm,
                "password_iterations": password_config.password_iterations,
                "is_active": is_active,
            },
        )
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError("User insertion did not return a row.")
        return row


def approve_registration_request(
    conn: ManagementConnection,
    *,
    request_id: str,
    admin_user_id: str,
    payload: RegistrationRequestReviewRequest,
) -> dict[str, Any] | None:
    """Approve a pending request and create the active provider user."""
    request = _get_registration_request_with_secret(conn, request_id)
    if request is None:
        return None
    if request["status"] != RegistrationRequestStatus.PENDING.value:
        raise UserManagementStateError("Only pending registration requests can be approved.")
    username = normalize_username(request["requested_username"])
    if find_user_by_username(conn, username) is not None:
        raise UserManagementConflictError("Username is already used by an active user.")
    provider_id = _validate_provider_id(conn, request["provider_id"], role=Role.PROVIDER)
    user = _insert_user(
        conn,
        username=username,
        display_name=request["display_name"],
        role=Role.PROVIDER,
        provider_id=provider_id,
        password_config=PasswordHashConfig(
            password_hash=request["pending_password_hash"],
            password_salt=request["pending_password_salt"],
            password_algorithm=request["pending_password_algorithm"],
            password_iterations=int(request["pending_password_iterations"]),
        ),
        is_active=True,
    )
    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            UPDATE user_registration_requests
            SET status = 'approved',
                reviewed_by_user_id = %(reviewed_by_user_id)s,
                reviewed_at = NOW(),
                review_notes = %(review_notes)s,
                created_user_id = %(created_user_id)s
            WHERE id = %(id)s
            RETURNING {SAFE_REGISTRATION_COLUMNS};
            """,
            {
                "id": request_id,
                "reviewed_by_user_id": admin_user_id,
                "review_notes": payload.review_notes,
                "created_user_id": user["id"],
            },
        )
        row = cursor.fetchone()
    _insert_admin_event(
        conn,
        actor_user_id=admin_user_id,
        target_user_id=str(user["id"]),
        registration_request_id=request_id,
        action="registration_request_approved",
        notes=payload.review_notes,
    )
    return row


def reject_registration_request(
    conn: ManagementConnection,
    *,
    request_id: str,
    admin_user_id: str,
    payload: RegistrationRequestReviewRequest,
) -> dict[str, Any] | None:
    """Reject a pending request without creating a user."""
    request = get_registration_request(conn, request_id)
    if request is None:
        return None
    if request["status"] != RegistrationRequestStatus.PENDING.value:
        raise UserManagementStateError("Only pending registration requests can be rejected.")
    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            UPDATE user_registration_requests
            SET status = 'rejected',
                reviewed_by_user_id = %(reviewed_by_user_id)s,
                reviewed_at = NOW(),
                review_notes = %(review_notes)s
            WHERE id = %(id)s
            RETURNING {SAFE_REGISTRATION_COLUMNS};
            """,
            {"id": request_id, "reviewed_by_user_id": admin_user_id, "review_notes": payload.review_notes},
        )
        row = cursor.fetchone()
    _insert_admin_event(
        conn,
        actor_user_id=admin_user_id,
        registration_request_id=request_id,
        action="registration_request_rejected",
        notes=payload.review_notes,
    )
    return row


def list_users(
    conn: ManagementConnection,
    *,
    role: Role | None = None,
    is_active: bool | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """List safe user records for admins."""
    clauses: list[str] = []
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if role is not None:
        clauses.append("role = %(role)s")
        params["role"] = role.value if isinstance(role, Role) else str(role)
    if is_active is not None:
        clauses.append("is_active = %(is_active)s")
        params["is_active"] = is_active
    if search:
        clauses.append("(username ILIKE %(search)s OR display_name ILIKE %(search)s OR COALESCE(provider_id, '') ILIKE %(search)s)")
        params["search"] = f"%{search.strip()}%"
    where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT {SAFE_USER_RETURNING}
            FROM auth_users
            {where_clause}
            ORDER BY created_at DESC, username ASC
            LIMIT %(limit)s OFFSET %(offset)s;
            """,
            params,
        )
        return cursor.fetchall()


def get_user(conn: ManagementConnection, user_id: str) -> dict[str, Any] | None:
    """Return one safe user by id."""
    with conn.cursor() as cursor:
        cursor.execute(f"SELECT {SAFE_USER_RETURNING} FROM auth_users WHERE id = %(user_id)s;", {"user_id": user_id})
        return cursor.fetchone()


def create_user(
    conn: ManagementConnection,
    *,
    payload: ManagedUserCreateRequest,
    admin_user_id: str,
) -> dict[str, Any]:
    """Create an active admin/provider user from an admin request."""
    username = normalize_username(payload.username)
    if find_user_by_username(conn, username) is not None:
        raise UserManagementConflictError("Username is already used by an active user.")
    role = Role(payload.role)
    provider_id = _validate_provider_id(conn, payload.provider_id, role=role)
    user = _insert_user(
        conn,
        username=username,
        display_name=payload.display_name,
        role=role,
        provider_id=provider_id,
        password_config=hash_password(payload.password),
        is_active=payload.is_active,
    )
    _insert_admin_event(conn, actor_user_id=admin_user_id, target_user_id=str(user["id"]), action="user_created")
    return user


def update_user(
    conn: ManagementConnection,
    *,
    user_id: str,
    payload: ManagedUserUpdateRequest,
    admin_user_id: str,
) -> dict[str, Any] | None:
    """Update safe user fields."""
    current = get_user(conn, user_id)
    if current is None:
        return None
    next_role = Role(payload.role or current["role"])
    next_provider_id = payload.provider_id if payload.provider_id is not None else current.get("provider_id")
    provider_id = _validate_provider_id(conn, next_provider_id, role=next_role)
    display_name = payload.display_name if payload.display_name is not None else current["display_name"]
    is_active = payload.is_active if payload.is_active is not None else current["is_active"]
    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            UPDATE auth_users
            SET display_name = %(display_name)s,
                role = %(role)s,
                provider_id = %(provider_id)s,
                is_active = %(is_active)s,
                updated_at = NOW()
            WHERE id = %(user_id)s
            RETURNING {SAFE_USER_RETURNING};
            """,
            {
                "user_id": user_id,
                "display_name": display_name.strip(),
                "role": next_role.value,
                "provider_id": provider_id,
                "is_active": is_active,
            },
        )
        row = cursor.fetchone()
    _insert_admin_event(conn, actor_user_id=admin_user_id, target_user_id=user_id, action="user_updated")
    return row


def reset_user_password(
    conn: ManagementConnection,
    *,
    user_id: str,
    payload: PasswordResetRequest,
    admin_user_id: str,
) -> dict[str, Any] | None:
    """Set a new password hash and optionally revoke existing sessions."""
    if get_user(conn, user_id) is None:
        return None
    password_config = hash_password(payload.new_password)
    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            UPDATE auth_users
            SET password_hash = %(password_hash)s,
                password_salt = %(password_salt)s,
                password_algorithm = %(password_algorithm)s,
                password_iterations = %(password_iterations)s,
                password_changed_at = NOW(),
                failed_login_count = 0,
                locked_until = NULL,
                updated_at = NOW()
            WHERE id = %(user_id)s
            RETURNING {SAFE_USER_RETURNING};
            """,
            {
                "user_id": user_id,
                "password_hash": password_config.password_hash,
                "password_salt": password_config.password_salt,
                "password_algorithm": password_config.password_algorithm,
                "password_iterations": password_config.password_iterations,
            },
        )
        row = cursor.fetchone()
    if row is not None and payload.revoke_existing_sessions:
        revoke_user_sessions(conn, user_id=user_id)
    _insert_admin_event(conn, actor_user_id=admin_user_id, target_user_id=user_id, action="password_reset")
    return row


def set_user_active(
    conn: ManagementConnection,
    *,
    user_id: str,
    is_active: bool,
    admin_user_id: str,
) -> bool | None:
    """Soft deactivate/reactivate a user."""
    if get_user(conn, user_id) is None:
        return None
    with conn.cursor() as cursor:
        cursor.execute(
            """
            UPDATE auth_users
            SET is_active = %(is_active)s,
                updated_at = NOW()
            WHERE id = %(user_id)s;
            """,
            {"user_id": user_id, "is_active": is_active},
        )
    if not is_active:
        revoke_user_sessions(conn, user_id=user_id)
    _insert_admin_event(
        conn,
        actor_user_id=admin_user_id,
        target_user_id=user_id,
        action="user_reactivated" if is_active else "user_deactivated",
    )
    return True


def list_user_sessions(conn: ManagementConnection, *, user_id: str) -> list[dict[str, Any]] | None:
    """List safe bearer-session metadata for a user."""
    if get_user(conn, user_id) is None:
        return None
    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT {SAFE_SESSION_COLUMNS}
            FROM auth_access_tokens
            WHERE user_id = %(user_id)s
            ORDER BY created_at DESC;
            """,
            {"user_id": user_id},
        )
        return cursor.fetchall()


def revoke_user_sessions(conn: ManagementConnection, *, user_id: str) -> int:
    """Revoke all active sessions for one user."""
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
        return int(getattr(cursor, "rowcount", 0) or 0)


def revoke_session(
    conn: ManagementConnection,
    *,
    user_id: str,
    session_id: str,
    admin_user_id: str,
) -> bool | None:
    """Revoke one user session if it belongs to the selected user."""
    if get_user(conn, user_id) is None:
        return None
    with conn.cursor() as cursor:
        cursor.execute(
            """
            UPDATE auth_access_tokens
            SET revoked_at = NOW()
            WHERE id = %(session_id)s
              AND user_id = %(user_id)s
              AND revoked_at IS NULL
            RETURNING id;
            """,
            {"session_id": session_id, "user_id": user_id},
        )
        changed = cursor.fetchone() is not None
    if changed:
        _insert_admin_event(conn, actor_user_id=admin_user_id, target_user_id=user_id, action="session_revoked")
    return changed
