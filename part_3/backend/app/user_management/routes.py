"""Controlled signup and admin user-management routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query, status

from backend.app.auth.dependencies import AdminRoutePrincipal
from backend.app.auth.models import Role
from backend.app.dependencies import DatabaseConnection
from backend.app.user_management.models import (
    ManagedUserCreateRequest,
    ManagedUserListResponse,
    ManagedUserResponse,
    ManagedUserUpdateRequest,
    PasswordResetRequest,
    RegistrationRequestCreateRequest,
    RegistrationRequestListResponse,
    RegistrationRequestResponse,
    RegistrationRequestReviewRequest,
    RegistrationRequestStatus,
    SessionListResponse,
    SessionRevokeResponse,
    UserActionResponse,
)
from backend.app.user_management.repositories import (
    UserManagementConflictError,
    UserManagementStateError,
    UserManagementValidationError,
    approve_registration_request,
    create_registration_request,
    create_user,
    get_registration_request,
    get_user,
    list_registration_requests,
    list_user_sessions,
    list_users,
    reject_registration_request,
    reset_user_password,
    revoke_session,
    set_user_active,
    update_user,
)

public_router = APIRouter(prefix="/auth", tags=["controlled signup"])
admin_router = APIRouter(prefix="/admin", tags=["admin user management"])

UserId = Annotated[UUID, Path(description="Database auth user id.")]
RequestId = Annotated[UUID, Path(description="Provider access request id.")]
SessionId = Annotated[UUID, Path(description="Database bearer session id.")]
AdminPrincipal = AdminRoutePrincipal


def _conflict(exc: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


def _bad_request(exc: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


def _not_found(resource: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{resource} was not found.")


def _admin_user_id(admin_principal: AdminPrincipal) -> str:
    return admin_principal.subject.removeprefix("user:")


@public_router.post(
    "/registration-requests",
    response_model=RegistrationRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_registration_request(
    payload: RegistrationRequestCreateRequest,
    conn: DatabaseConnection,
) -> dict:
    """Create a pending provider access request without logging the user in."""
    try:
        return create_registration_request(conn, payload=payload)
    except UserManagementConflictError as exc:
        raise _conflict(exc) from exc
    except UserManagementValidationError as exc:
        raise _bad_request(exc) from exc


@admin_router.get("/registration-requests", response_model=RegistrationRequestListResponse)
def get_registration_requests(
    conn: DatabaseConnection,
    admin_principal: AdminPrincipal,
    request_status: Annotated[RegistrationRequestStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    """List provider signup/access requests for admins."""
    items = list_registration_requests(conn, status=request_status, limit=limit, offset=offset)
    return {"items": items, "limit": limit, "offset": offset}


@admin_router.get("/registration-requests/{request_id}", response_model=RegistrationRequestResponse)
def get_registration_request_detail(
    request_id: RequestId,
    conn: DatabaseConnection,
    admin_principal: AdminPrincipal,
) -> dict:
    """Read one provider access request."""
    row = get_registration_request(conn, str(request_id))
    if row is None:
        raise _not_found("Registration request")
    return row


@admin_router.post("/registration-requests/{request_id}/approve", response_model=RegistrationRequestResponse)
def post_approve_registration_request(
    request_id: RequestId,
    payload: RegistrationRequestReviewRequest,
    conn: DatabaseConnection,
    admin_principal: AdminPrincipal,
) -> dict:
    """Approve a pending request and create an active provider user."""
    try:
        row = approve_registration_request(
            conn,
            request_id=str(request_id),
            admin_user_id=_admin_user_id(admin_principal),
            payload=payload,
        )
    except UserManagementConflictError as exc:
        raise _conflict(exc) from exc
    except UserManagementValidationError as exc:
        raise _bad_request(exc) from exc
    except UserManagementStateError as exc:
        raise _conflict(exc) from exc
    if row is None:
        raise _not_found("Registration request")
    return row


@admin_router.post("/registration-requests/{request_id}/reject", response_model=RegistrationRequestResponse)
def post_reject_registration_request(
    request_id: RequestId,
    payload: RegistrationRequestReviewRequest,
    conn: DatabaseConnection,
    admin_principal: AdminPrincipal,
) -> dict:
    """Reject a pending request without creating a user."""
    try:
        row = reject_registration_request(
            conn,
            request_id=str(request_id),
            admin_user_id=_admin_user_id(admin_principal),
            payload=payload,
        )
    except UserManagementStateError as exc:
        raise _conflict(exc) from exc
    if row is None:
        raise _not_found("Registration request")
    return row


@admin_router.get("/users", response_model=ManagedUserListResponse)
def get_users(
    conn: DatabaseConnection,
    admin_principal: AdminPrincipal,
    role: Role | None = None,
    is_active: bool | None = None,
    search: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    """List safe user records for admins."""
    return {
        "items": list_users(conn, role=role, is_active=is_active, search=search, limit=limit, offset=offset),
        "limit": limit,
        "offset": offset,
    }


@admin_router.post("/users", response_model=ManagedUserResponse, status_code=status.HTTP_201_CREATED)
def post_user(
    payload: ManagedUserCreateRequest,
    conn: DatabaseConnection,
    admin_principal: AdminPrincipal,
) -> dict:
    """Create an active admin or provider user."""
    try:
        return create_user(conn, payload=payload, admin_user_id=_admin_user_id(admin_principal))
    except UserManagementConflictError as exc:
        raise _conflict(exc) from exc
    except UserManagementValidationError as exc:
        raise _bad_request(exc) from exc


@admin_router.get("/users/{user_id}", response_model=ManagedUserResponse)
def get_user_detail(user_id: UserId, conn: DatabaseConnection, admin_principal: AdminPrincipal) -> dict:
    """Read safe metadata for one user."""
    row = get_user(conn, str(user_id))
    if row is None:
        raise _not_found("User")
    return row


@admin_router.patch("/users/{user_id}", response_model=ManagedUserResponse)
def patch_user(
    user_id: UserId,
    payload: ManagedUserUpdateRequest,
    conn: DatabaseConnection,
    admin_principal: AdminPrincipal,
) -> dict:
    """Update safe user fields."""
    try:
        row = update_user(conn, user_id=str(user_id), payload=payload, admin_user_id=_admin_user_id(admin_principal))
    except UserManagementValidationError as exc:
        raise _bad_request(exc) from exc
    if row is None:
        raise _not_found("User")
    return row


@admin_router.post("/users/{user_id}/reset-password", response_model=ManagedUserResponse)
def post_reset_password(
    user_id: UserId,
    payload: PasswordResetRequest,
    conn: DatabaseConnection,
    admin_principal: AdminPrincipal,
) -> dict:
    """Reset one user's password without returning it."""
    row = reset_user_password(conn, user_id=str(user_id), payload=payload, admin_user_id=_admin_user_id(admin_principal))
    if row is None:
        raise _not_found("User")
    return row


@admin_router.post("/users/{user_id}/deactivate", response_model=UserActionResponse)
def post_deactivate_user(user_id: UserId, conn: DatabaseConnection, admin_principal: AdminPrincipal) -> dict:
    """Soft-disable a user and revoke active sessions."""
    changed = set_user_active(conn, user_id=str(user_id), is_active=False, admin_user_id=_admin_user_id(admin_principal))
    if changed is None:
        raise _not_found("User")
    return {"id": user_id, "changed": changed}


@admin_router.post("/users/{user_id}/reactivate", response_model=UserActionResponse)
def post_reactivate_user(user_id: UserId, conn: DatabaseConnection, admin_principal: AdminPrincipal) -> dict:
    """Reactivate a soft-disabled user."""
    changed = set_user_active(conn, user_id=str(user_id), is_active=True, admin_user_id=_admin_user_id(admin_principal))
    if changed is None:
        raise _not_found("User")
    return {"id": user_id, "changed": changed}


@admin_router.get("/users/{user_id}/sessions", response_model=SessionListResponse)
def get_user_sessions(user_id: UserId, conn: DatabaseConnection, admin_principal: AdminPrincipal) -> dict:
    """Inspect safe bearer-session metadata for one user."""
    rows = list_user_sessions(conn, user_id=str(user_id))
    if rows is None:
        raise _not_found("User")
    return {"items": rows}


@admin_router.post("/users/{user_id}/sessions/{session_id}/revoke", response_model=SessionRevokeResponse)
def post_revoke_user_session(
    user_id: UserId,
    session_id: SessionId,
    conn: DatabaseConnection,
    admin_principal: AdminPrincipal,
) -> dict:
    """Revoke one bearer session for one user."""
    changed = revoke_session(
        conn,
        user_id=str(user_id),
        session_id=str(session_id),
        admin_user_id=_admin_user_id(admin_principal),
    )
    if changed is None:
        raise _not_found("User")
    return {"id": session_id, "revoked": changed}
