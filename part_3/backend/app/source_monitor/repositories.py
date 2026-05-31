"""Raw-SQL repository helpers for MYH source monitoring."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import psycopg


def _row_dict(row: Any) -> dict[str, Any] | None:
    """Return a plain dict for psycopg dict rows and tuple-like rows."""
    if row is None:
        return None
    if isinstance(row, dict):
        return dict(row)
    try:
        return dict(row)
    except Exception:
        return row  # type: ignore[return-value]


def create_check_run(conn: psycopg.Connection[dict[str, Any]], *, source_url: str) -> dict[str, Any]:
    """Create a source-check run row."""
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO myh_source_check_runs (id, source_url, status, started_at)
            VALUES (%(id)s, %(source_url)s, 'running', NOW())
            RETURNING *;
            """,
            {"id": str(uuid4()), "source_url": source_url},
        )
        return _row_dict(cursor.fetchone()) or {}


def finish_check_run(
    conn: psycopg.Connection[dict[str, Any]],
    *,
    check_run_id: str | UUID,
    status: str,
    http_status: int | None,
    discovered_count: int,
    new_count: int,
    changed_count: int,
    known_count: int,
    message: str,
    error_message: str | None = None,
) -> dict[str, Any]:
    """Finish one source-check run and return it."""
    with conn.cursor() as cursor:
        cursor.execute(
            """
            UPDATE myh_source_check_runs
            SET status = %(status)s,
                finished_at = NOW(),
                http_status = %(http_status)s,
                discovered_count = %(discovered_count)s,
                new_count = %(new_count)s,
                changed_count = %(changed_count)s,
                known_count = %(known_count)s,
                message = %(message)s,
                error_message = %(error_message)s
            WHERE id = %(id)s
            RETURNING *;
            """,
            {
                "id": str(check_run_id),
                "status": status,
                "http_status": http_status,
                "discovered_count": discovered_count,
                "new_count": new_count,
                "changed_count": changed_count,
                "known_count": known_count,
                "message": message,
                "error_message": error_message,
            },
        )
        return _row_dict(cursor.fetchone()) or {}


def find_source_file_by_url(conn: psycopg.Connection[dict[str, Any]], file_url: str) -> dict[str, Any] | None:
    """Find a stored source file by canonical URL."""
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM myh_source_files WHERE file_url = %(file_url)s;", {"file_url": file_url})
        return _row_dict(cursor.fetchone())


def create_source_file(
    conn: psycopg.Connection[dict[str, Any]],
    *,
    file_name: str,
    file_url: str,
    file_type: str,
    source_year: int | None,
    check_run_id: str | UUID,
) -> dict[str, Any]:
    """Insert one newly detected official source file."""
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO myh_source_files (
                id, file_name, file_url, file_type, source_year, status,
                first_seen_at, last_seen_at, last_checked_at, first_check_run_id, last_check_run_id
            )
            VALUES (
                %(id)s, %(file_name)s, %(file_url)s, %(file_type)s, %(source_year)s, 'new',
                NOW(), NOW(), NOW(), %(check_run_id)s, %(check_run_id)s
            )
            RETURNING *;
            """,
            {
                "id": str(uuid4()),
                "file_name": file_name,
                "file_url": file_url,
                "file_type": file_type,
                "source_year": source_year,
                "check_run_id": str(check_run_id),
            },
        )
        return _row_dict(cursor.fetchone()) or {}


def update_seen_source_file(
    conn: psycopg.Connection[dict[str, Any]],
    *,
    source_file_id: str | UUID,
    file_name: str,
    file_type: str,
    source_year: int | None,
    status: str,
    check_run_id: str | UUID,
) -> dict[str, Any]:
    """Update metadata for a known or changed source file."""
    with conn.cursor() as cursor:
        cursor.execute(
            """
            UPDATE myh_source_files
            SET file_name = %(file_name)s,
                file_type = %(file_type)s,
                source_year = %(source_year)s,
                status = %(status)s,
                last_seen_at = NOW(),
                last_checked_at = NOW(),
                last_check_run_id = %(check_run_id)s,
                updated_at = NOW()
            WHERE id = %(id)s
            RETURNING *;
            """,
            {
                "id": str(source_file_id),
                "file_name": file_name,
                "file_type": file_type,
                "source_year": source_year,
                "status": status,
                "check_run_id": str(check_run_id),
            },
        )
        return _row_dict(cursor.fetchone()) or {}


def get_source_file(conn: psycopg.Connection[dict[str, Any]], source_file_id: str | UUID) -> dict[str, Any] | None:
    """Return one stored source file."""
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM myh_source_files WHERE id = %(id)s;", {"id": str(source_file_id)})
        return _row_dict(cursor.fetchone())


def list_source_files(conn: psycopg.Connection[dict[str, Any]], *, limit: int, offset: int) -> dict[str, Any]:
    """List source files with a total count."""
    with conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) AS total FROM myh_source_files;")
        count_row = _row_dict(cursor.fetchone()) or {"total": 0}
        cursor.execute(
            """
            SELECT *
            FROM myh_source_files
            ORDER BY COALESCE(source_year, 0) DESC, last_seen_at DESC, file_name ASC
            LIMIT %(limit)s OFFSET %(offset)s;
            """,
            {"limit": limit, "offset": offset},
        )
        return {"items": [_row_dict(row) for row in cursor.fetchall()], "total": int(count_row["total"]), "limit": limit, "offset": offset}


def update_download_metadata(
    conn: psycopg.Connection[dict[str, Any]],
    *,
    source_file_id: str | UUID,
    sha256: str,
    downloaded_path: str,
    size_bytes: int,
    changed: bool,
) -> dict[str, Any]:
    """Store download metadata and mark content changes when the hash differs."""
    status = "changed" if changed else "known"
    with conn.cursor() as cursor:
        cursor.execute(
            """
            UPDATE myh_source_files
            SET last_sha256 = %(sha256)s,
                downloaded_path = %(downloaded_path)s,
                last_download_size_bytes = %(size_bytes)s,
                last_downloaded_at = NOW(),
                status = %(status)s,
                last_error = NULL,
                updated_at = NOW()
            WHERE id = %(id)s
            RETURNING *;
            """,
            {
                "id": str(source_file_id),
                "sha256": sha256,
                "downloaded_path": downloaded_path,
                "size_bytes": size_bytes,
                "status": status,
            },
        )
        return _row_dict(cursor.fetchone()) or {}




def mark_source_file_imported(conn: psycopg.Connection[dict[str, Any]], *, source_file_id: str | UUID) -> None:
    """Mark a source file as successfully imported."""
    with conn.cursor() as cursor:
        cursor.execute(
            """
            UPDATE myh_source_files
            SET status = 'imported', last_error = NULL, updated_at = NOW()
            WHERE id = %(id)s;
            """,
            {"id": str(source_file_id)},
        )


def update_source_file_error(conn: psycopg.Connection[dict[str, Any]], *, source_file_id: str | UUID, error: str) -> None:
    """Record the latest source-file operation error."""
    with conn.cursor() as cursor:
        cursor.execute(
            """
            UPDATE myh_source_files
            SET last_error = %(error)s, updated_at = NOW()
            WHERE id = %(id)s;
            """,
            {"id": str(source_file_id), "error": error},
        )


def create_refresh_run(
    conn: psycopg.Connection[dict[str, Any]],
    *,
    mode: str,
    source_file_id: str | UUID | None,
    triggered_by_user_id: str | UUID | None,
) -> dict[str, Any]:
    """Create a refresh/import run row."""
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO myh_refresh_runs (id, source_file_id, status, mode, started_at, triggered_by_user_id)
            VALUES (%(id)s, %(source_file_id)s, 'running', %(mode)s, NOW(), %(triggered_by_user_id)s)
            RETURNING *;
            """,
            {
                "id": str(uuid4()),
                "source_file_id": str(source_file_id) if source_file_id else None,
                "mode": mode,
                "triggered_by_user_id": str(triggered_by_user_id) if triggered_by_user_id else None,
            },
        )
        return _row_dict(cursor.fetchone()) or {}


def finish_refresh_run(
    conn: psycopg.Connection[dict[str, Any]],
    *,
    refresh_run_id: str | UUID,
    status: str,
    rows_imported: int | None = None,
    affected_years: str | None = None,
    source_sha256: str | None = None,
    downloaded_path: str | None = None,
    processed_path: str | None = None,
    validation_summary: str | None = None,
    error_message: str | None = None,
) -> dict[str, Any]:
    """Finish a refresh/import run."""
    with conn.cursor() as cursor:
        cursor.execute(
            """
            UPDATE myh_refresh_runs
            SET status = %(status)s,
                finished_at = NOW(),
                rows_imported = %(rows_imported)s,
                affected_years = %(affected_years)s,
                source_sha256 = %(source_sha256)s,
                downloaded_path = %(downloaded_path)s,
                processed_path = %(processed_path)s,
                validation_summary = %(validation_summary)s,
                error_message = %(error_message)s
            WHERE id = %(id)s
            RETURNING *;
            """,
            {
                "id": str(refresh_run_id),
                "status": status,
                "rows_imported": rows_imported,
                "affected_years": affected_years,
                "source_sha256": source_sha256,
                "downloaded_path": downloaded_path,
                "processed_path": processed_path,
                "validation_summary": validation_summary,
                "error_message": error_message,
            },
        )
        return _row_dict(cursor.fetchone()) or {}


def get_refresh_run(conn: psycopg.Connection[dict[str, Any]], refresh_run_id: str | UUID) -> dict[str, Any] | None:
    """Return one refresh run."""
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM myh_refresh_runs WHERE id = %(id)s;", {"id": str(refresh_run_id)})
        return _row_dict(cursor.fetchone())


def list_refresh_runs(conn: psycopg.Connection[dict[str, Any]], *, limit: int, offset: int) -> dict[str, Any]:
    """List refresh runs with a total count."""
    with conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) AS total FROM myh_refresh_runs;")
        count_row = _row_dict(cursor.fetchone()) or {"total": 0}
        cursor.execute(
            """
            SELECT *
            FROM myh_refresh_runs
            ORDER BY started_at DESC
            LIMIT %(limit)s OFFSET %(offset)s;
            """,
            {"limit": limit, "offset": offset},
        )
        return {"items": [_row_dict(row) for row in cursor.fetchall()], "total": int(count_row["total"]), "limit": limit, "offset": offset}


def latest_check_run(conn: psycopg.Connection[dict[str, Any]]) -> dict[str, Any] | None:
    """Return the newest source-check run."""
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM myh_source_check_runs ORDER BY started_at DESC LIMIT 1;")
        return _row_dict(cursor.fetchone())


def latest_refresh_run(conn: psycopg.Connection[dict[str, Any]]) -> dict[str, Any] | None:
    """Return the newest refresh run."""
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM myh_refresh_runs ORDER BY started_at DESC LIMIT 1;")
        return _row_dict(cursor.fetchone())


def count_source_files(conn: psycopg.Connection[dict[str, Any]]) -> int:
    """Return source file count."""
    with conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) AS total FROM myh_source_files;")
        row = _row_dict(cursor.fetchone()) or {"total": 0}
        return int(row["total"])


def count_unread_notifications(conn: psycopg.Connection[dict[str, Any]]) -> int:
    """Return unread admin notification count."""
    with conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) AS total FROM admin_notifications WHERE status = 'unread';")
        row = _row_dict(cursor.fetchone()) or {"total": 0}
        return int(row["total"])


def create_notification(
    conn: psycopg.Connection[dict[str, Any]],
    *,
    notification_type: str,
    severity: str,
    title: str,
    message: str,
    source_file_id: str | UUID | None = None,
    refresh_run_id: str | UUID | None = None,
    actor_user_id: str | UUID | None = None,
) -> dict[str, Any]:
    """Create an unread admin notification."""
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO admin_notifications (
                id, notification_type, severity, title, message, status,
                source_file_id, refresh_run_id, actor_user_id, created_at
            )
            VALUES (
                %(id)s, %(notification_type)s, %(severity)s, %(title)s, %(message)s, 'unread',
                %(source_file_id)s, %(refresh_run_id)s, %(actor_user_id)s, NOW()
            )
            RETURNING *;
            """,
            {
                "id": str(uuid4()),
                "notification_type": notification_type,
                "severity": severity,
                "title": title,
                "message": message,
                "source_file_id": str(source_file_id) if source_file_id else None,
                "refresh_run_id": str(refresh_run_id) if refresh_run_id else None,
                "actor_user_id": str(actor_user_id) if actor_user_id else None,
            },
        )
        return _row_dict(cursor.fetchone()) or {}


def list_notifications(
    conn: psycopg.Connection[dict[str, Any]],
    *,
    status: str | None,
    limit: int,
    offset: int,
) -> dict[str, Any]:
    """List admin notifications with optional status filter."""
    where = "WHERE status = %(status)s" if status else ""
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if status:
        params["status"] = status
    with conn.cursor() as cursor:
        cursor.execute(f"SELECT COUNT(*) AS total FROM admin_notifications {where};", params)
        count_row = _row_dict(cursor.fetchone()) or {"total": 0}
        cursor.execute(
            f"""
            SELECT *
            FROM admin_notifications
            {where}
            ORDER BY created_at DESC
            LIMIT %(limit)s OFFSET %(offset)s;
            """,
            params,
        )
        return {"items": [_row_dict(row) for row in cursor.fetchall()], "total": int(count_row["total"]), "limit": limit, "offset": offset}


def update_notification_status(
    conn: psycopg.Connection[dict[str, Any]],
    *,
    notification_id: str | UUID,
    status: str,
    actor_user_id: str | UUID | None,
) -> dict[str, Any] | None:
    """Mark an admin notification read or resolved."""
    timestamp_field = "read_at" if status == "read" else "resolved_at"
    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            UPDATE admin_notifications
            SET status = %(status)s,
                {timestamp_field} = NOW(),
                actor_user_id = COALESCE(%(actor_user_id)s, actor_user_id)
            WHERE id = %(id)s
            RETURNING *;
            """,
            {"id": str(notification_id), "status": status, "actor_user_id": str(actor_user_id) if actor_user_id else None},
        )
        return _row_dict(cursor.fetchone())
