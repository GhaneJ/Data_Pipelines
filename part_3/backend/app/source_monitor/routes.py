"""Admin routes for source monitoring, notifications, and refresh runs."""

from __future__ import annotations

import logging
from typing import Annotated, Any
from uuid import UUID

import psycopg
from fastapi import APIRouter, Body, HTTPException, Path, Query, status

from backend.app.auth.dependencies import AdminRoutePrincipal
from backend.app.dependencies import DatabaseConnection
from backend.app.source_monitor.models import (
    AdminNotification,
    AdminNotificationList,
    RefreshRequest,
    RefreshRun,
    RefreshRunList,
    SourceCheckResponse,
    SourceFile,
    SourceFileDownloadResponse,
    SourceFileList,
    SourceMonitorStatus,
)
from backend.app.source_monitor import repositories as repo
from backend.app.source_monitor.service import (
    build_status,
    download_source_file,
    import_source_file,
    refresh_from_curated_csv_compatibility,
    run_source_check,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["source-monitor"])
AdminPrincipal = AdminRoutePrincipal
PositiveLimit = Annotated[int, Query(ge=1, le=200)]
Offset = Annotated[int, Query(ge=0)]
SourceFileId = Annotated[UUID, Path(description="Stored MYH source file id.")]
RefreshRunId = Annotated[UUID, Path(description="Refresh run id.")]
NotificationId = Annotated[UUID, Path(description="Admin notification id.")]


def _actor_id(admin_principal: Any) -> str:
    return str(admin_principal.subject).removeprefix("user:")


def _not_found(label: str, identifier: UUID) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} {identifier} was not found.")


@router.get("/admin/source-monitor/status", response_model=SourceMonitorStatus)
def get_source_monitor_status(conn: DatabaseConnection, admin_principal: AdminPrincipal) -> dict[str, Any]:
    """Return the current source-monitor status for admins."""
    return build_status(conn)


@router.post("/admin/source-monitor/check", response_model=SourceCheckResponse)
def post_source_monitor_check(conn: DatabaseConnection, admin_principal: AdminPrincipal) -> dict[str, Any]:
    """Run an admin-triggered MYH source-page check."""
    return run_source_check(conn, actor_user_id=_actor_id(admin_principal))


@router.get("/admin/source-files", response_model=SourceFileList)
def get_source_files(
    conn: DatabaseConnection,
    admin_principal: AdminPrincipal,
    limit: PositiveLimit = 50,
    offset: Offset = 0,
) -> dict[str, Any]:
    """List detected MYH source files."""
    return repo.list_source_files(conn, limit=limit, offset=offset)


@router.get("/admin/source-files/{source_file_id}", response_model=SourceFile)
def get_source_file(source_file_id: SourceFileId, conn: DatabaseConnection, admin_principal: AdminPrincipal) -> dict[str, Any]:
    """Return one detected MYH source-file record."""
    source_file = repo.get_source_file(conn, source_file_id)
    if source_file is None:
        raise _not_found("Source file", source_file_id)
    return source_file


@router.post("/admin/source-files/{source_file_id}/download", response_model=SourceFileDownloadResponse)
def post_download_source_file(
    source_file_id: SourceFileId,
    conn: DatabaseConnection,
    admin_principal: AdminPrincipal,
) -> dict[str, Any]:
    """Download and hash one detected official source file."""
    try:
        return download_source_file(conn, source_file_id=str(source_file_id))
    except FileNotFoundError as exc:
        raise _not_found("Source file", source_file_id) from exc
    except Exception as exc:
        logger.warning("Source file download failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/admin/source-files/{source_file_id}/import", response_model=RefreshRun)
def post_import_source_file(
    source_file_id: SourceFileId,
    conn: DatabaseConnection,
    admin_principal: AdminPrincipal,
) -> dict[str, Any]:
    """Validate and import one downloaded official source file."""
    try:
        return import_source_file(conn, source_file_id=str(source_file_id), actor_user_id=_actor_id(admin_principal))
    except FileNotFoundError as exc:
        raise _not_found("Source file", source_file_id) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except psycopg.Error as exc:
        logger.exception("Refresh import failed in PostgreSQL.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database refresh import failed.") from exc


@router.get("/admin/refresh-runs", response_model=RefreshRunList)
def get_refresh_runs(
    conn: DatabaseConnection,
    admin_principal: AdminPrincipal,
    limit: PositiveLimit = 50,
    offset: Offset = 0,
) -> dict[str, Any]:
    """List refresh/import run history."""
    return repo.list_refresh_runs(conn, limit=limit, offset=offset)


@router.get("/admin/refresh-runs/{refresh_run_id}", response_model=RefreshRun)
def get_refresh_run(refresh_run_id: RefreshRunId, conn: DatabaseConnection, admin_principal: AdminPrincipal) -> dict[str, Any]:
    """Return one refresh/import run."""
    refresh_run = repo.get_refresh_run(conn, refresh_run_id)
    if refresh_run is None:
        raise _not_found("Refresh run", refresh_run_id)
    return refresh_run


@router.get("/admin/notifications", response_model=AdminNotificationList)
def get_notifications(
    conn: DatabaseConnection,
    admin_principal: AdminPrincipal,
    notification_status: Annotated[str | None, Query(pattern="^(unread|read|resolved)$")] = None,
    limit: PositiveLimit = 50,
    offset: Offset = 0,
) -> dict[str, Any]:
    """List admin operations notifications."""
    return repo.list_notifications(conn, status=notification_status, limit=limit, offset=offset)


@router.post("/admin/notifications/{notification_id}/read", response_model=AdminNotification)
def post_mark_notification_read(
    notification_id: NotificationId,
    conn: DatabaseConnection,
    admin_principal: AdminPrincipal,
) -> dict[str, Any]:
    """Mark one admin notification as read."""
    notification = repo.update_notification_status(conn, notification_id=notification_id, status="read", actor_user_id=_actor_id(admin_principal))
    if notification is None:
        raise _not_found("Notification", notification_id)
    return notification


@router.post("/admin/notifications/{notification_id}/resolve", response_model=AdminNotification)
def post_resolve_notification(
    notification_id: NotificationId,
    conn: DatabaseConnection,
    admin_principal: AdminPrincipal,
) -> dict[str, Any]:
    """Resolve one admin notification."""
    notification = repo.update_notification_status(conn, notification_id=notification_id, status="resolved", actor_user_id=_actor_id(admin_principal))
    if notification is None:
        raise _not_found("Notification", notification_id)
    return notification


@router.post("/refresh", response_model=RefreshRun)
def post_refresh(
    conn: DatabaseConnection,
    admin_principal: AdminPrincipal,
    payload: Annotated[RefreshRequest | None, Body()] = None,
    source_file_id: Annotated[UUID | None, Query(description="Optional source file id for compatibility callers.")] = None,
) -> dict[str, Any]:
    """Compatibility refresh endpoint routed through the robust 3.20 service.

    Admin bearer auth is required. API keys, providers, and public users cannot
    trigger refresh/import operations.
    """
    selected_source_file_id = source_file_id or (payload.source_file_id if payload else None)
    try:
        if selected_source_file_id:
            return import_source_file(conn, source_file_id=str(selected_source_file_id), actor_user_id=_actor_id(admin_principal))
        return refresh_from_curated_csv_compatibility(conn, actor_user_id=_actor_id(admin_principal))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except psycopg.Error as exc:
        logger.exception("Compatibility refresh failed in PostgreSQL.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database refresh failed.") from exc
