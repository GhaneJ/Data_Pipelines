"""Database-backed authentication routes."""

from __future__ import annotations

from datetime import UTC, timedelta
from typing import Any

from fastapi import APIRouter, Header, HTTPException, status

from backend.app.auth.dependencies import CurrentPrincipal, parse_bearer_token
from backend.app.auth.models import LoginRequest, LoginResponse, LogoutResponse, WhoamiResponse
from backend.app.auth.password_hashing import verify_password
from backend.app.auth.repositories import (
    clear_failed_login_state,
    create_access_token_record,
    find_user_by_username,
    increment_failed_login_count,
    principal_from_user_row,
    revoke_access_token_hash,
)
from backend.app.auth.tokens import access_token_expiry, generate_access_token, hash_access_token, utc_now
from backend.app.dependencies import DatabaseConnection


router = APIRouter(prefix="/auth", tags=["auth"])

AUTHORIZATION_HEADER = "Authorization"
FAILED_LOGIN_LOCK_THRESHOLD = 5
LOCKOUT_MINUTES = 15
_INVALID_LOGIN = "Invalid username or password."
_INACTIVE_LOGIN = "Authentication is not available for this user."
_LOCKED_LOGIN = "Authentication is temporarily unavailable for this user."


def _unauthorized(message: str) -> HTTPException:
    """Build a safe 401 auth failure."""
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message)


def _row_is_locked(row: dict[str, Any]) -> bool:
    """Return whether the user row is currently locked."""
    locked_until = row.get("locked_until")
    if locked_until is None:
        return False
    if locked_until.tzinfo is None:
        locked_until = locked_until.replace(tzinfo=UTC)
    return locked_until > utc_now()


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, conn: DatabaseConnection) -> LoginResponse:
    """Authenticate a database user and issue an opaque bearer token."""
    user = find_user_by_username(conn, payload.username)
    if user is None:
        # Keep the response indistinguishable from a bad password.
        raise _unauthorized(_INVALID_LOGIN)

    if not user.get("is_active", False):
        raise _unauthorized(_INACTIVE_LOGIN)
    if _row_is_locked(user):
        raise _unauthorized(_LOCKED_LOGIN)

    password_ok = verify_password(
        payload.password,
        stored_hash=user["password_hash"],
        stored_salt=user["password_salt"],
        algorithm=user["password_algorithm"],
        iterations=int(user["password_iterations"]),
    )
    if not password_ok:
        locked_until = utc_now() + timedelta(minutes=LOCKOUT_MINUTES)
        increment_failed_login_count(
            conn,
            user_id=str(user["id"]),
            lock_threshold=FAILED_LOGIN_LOCK_THRESHOLD,
            locked_until=locked_until,
        )
        raise _unauthorized(_INVALID_LOGIN)

    clear_failed_login_state(conn, user_id=str(user["id"]))
    raw_token = generate_access_token()
    expires_at = access_token_expiry()
    create_access_token_record(
        conn,
        user_id=str(user["id"]),
        token_hash=hash_access_token(raw_token),
        expires_at=expires_at,
    )
    return LoginResponse(access_token=raw_token, expires_at=expires_at)


@router.get("/whoami", response_model=WhoamiResponse)
def whoami(principal: CurrentPrincipal) -> WhoamiResponse:
    """Return the safe authenticated principal for a valid bearer token."""
    return WhoamiResponse(**principal.model_dump())


@router.post("/logout", response_model=LogoutResponse)
def logout(
    conn: DatabaseConnection,
    authorization: str | None = Header(default=None, alias=AUTHORIZATION_HEADER),
) -> LogoutResponse:
    """Revoke the current database-issued bearer token."""
    raw_token = parse_bearer_token(authorization)
    # The dependency is not reused here because logout should revoke only this
    # raw token while still returning a safe success payload.
    revoked = revoke_access_token_hash(conn, token_hash=hash_access_token(raw_token))
    if not revoked:
        raise _unauthorized("Invalid authentication token.")
    return LogoutResponse(revoked=True)
