"""Pydantic models for MYH source-monitoring operations."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SourceFileCandidate(BaseModel):
    """One official source file link discovered on the MYH page."""

    file_name: str
    file_url: str
    file_type: str
    source_year: int | None = None
    label: str | None = None


class SourceMonitorStatus(BaseModel):
    """Admin status summary for the source monitor."""

    monitor_enabled: bool
    run_on_startup: bool
    auto_import_enabled: bool
    interval_minutes: int
    source_url: str
    last_check: dict | None = None
    known_source_files: int
    unread_notifications: int
    latest_refresh_run: dict | None = None


class SourceCheckResponse(BaseModel):
    """Result from one source page check."""

    check_run_id: UUID
    status: str
    source_url: str
    started_at: datetime
    finished_at: datetime | None = None
    http_status: int | None = None
    discovered_count: int
    new_count: int
    changed_count: int
    known_count: int
    message: str
    error_message: str | None = None
    files: list[dict]


class SourceFile(BaseModel):
    """Stored source file metadata."""

    id: UUID
    file_name: str
    file_url: str
    file_type: str
    source_year: int | None = None
    status: str
    first_seen_at: datetime
    last_seen_at: datetime
    last_checked_at: datetime | None = None
    last_downloaded_at: datetime | None = None
    last_sha256: str | None = None
    downloaded_path: str | None = None
    last_error: str | None = None


class SourceFileList(BaseModel):
    """Paginated source file response."""

    items: list[SourceFile]
    total: int
    limit: int
    offset: int


class SourceFileDownloadResponse(BaseModel):
    """Download result for one official source file."""

    source_file_id: UUID
    file_name: str
    downloaded_path: str
    sha256: str
    size_bytes: int
    changed: bool
    message: str


class RefreshRun(BaseModel):
    """Stored refresh/import run metadata."""

    id: UUID
    source_file_id: UUID | None = None
    status: str
    mode: str
    started_at: datetime
    finished_at: datetime | None = None
    rows_imported: int | None = None
    affected_years: str | None = None
    source_sha256: str | None = None
    downloaded_path: str | None = None
    processed_path: str | None = None
    validation_summary: str | None = None
    error_message: str | None = None
    triggered_by_user_id: UUID | None = None


class RefreshRunList(BaseModel):
    """Paginated refresh run response."""

    items: list[RefreshRun]
    total: int
    limit: int
    offset: int


class AdminNotification(BaseModel):
    """Admin notification shown in the operations workspace."""

    id: UUID
    notification_type: str
    severity: str
    title: str
    message: str
    status: str
    source_file_id: UUID | None = None
    refresh_run_id: UUID | None = None
    created_at: datetime
    read_at: datetime | None = None
    resolved_at: datetime | None = None
    actor_user_id: UUID | None = None


class AdminNotificationList(BaseModel):
    """Paginated admin notification response."""

    items: list[AdminNotification]
    total: int
    limit: int
    offset: int


class RefreshRequest(BaseModel):
    """Optional compatibility refresh payload for POST /refresh."""

    source_file_id: UUID | None = Field(default=None, description="Import this detected official source file when provided.")
