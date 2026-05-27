"""Focused tests for protected admin-note service helpers."""

from __future__ import annotations

import pytest

from backend.app.services import admin_notes


class RecordingCursor:
    """Tiny cursor double for service tests that do not need PostgreSQL."""

    def __init__(self, connection: "RecordingConnection") -> None:
        self.connection = connection

    def __enter__(self) -> "RecordingCursor":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    def execute(self, sql: str, params: dict[str, object] | None = None) -> None:
        self.connection.executed.append((sql, params or {}))

    def fetchone(self) -> dict[str, object] | None:
        if not self.connection.fetchone_results:
            return None
        return self.connection.fetchone_results.pop(0)

    def fetchall(self) -> list[dict[str, object]]:
        return list(self.connection.fetchall_result)


class RecordingConnection:
    """Connection double returning preloaded fetch results."""

    def __init__(self) -> None:
        self.executed: list[tuple[str, dict[str, object]]] = []
        self.fetchone_results: list[dict[str, object] | None] = []
        self.fetchall_result: list[dict[str, object]] = []

    def cursor(self) -> RecordingCursor:
        return RecordingCursor(self)


def test_normalize_note_text_rejects_blank_text() -> None:
    """Admin notes should not store empty local metadata."""
    with pytest.raises(ValueError, match="must not be empty"):
        admin_notes.normalize_note_text("   ")


def test_normalize_note_text_rejects_overly_long_text() -> None:
    """The local note feature should stay deliberately small."""
    with pytest.raises(ValueError, match="at most"):
        admin_notes.normalize_note_text("x" * (admin_notes.MAX_NOTE_TEXT_LENGTH + 1))


def test_normalize_note_text_trims_valid_text() -> None:
    """Stored notes should not keep accidental outer whitespace."""
    assert admin_notes.normalize_note_text("  Follow up before demo.  ") == "Follow up before demo."


def test_create_application_note_validates_application_before_insert() -> None:
    """The write service should only add notes for existing applications."""
    conn = RecordingConnection()
    conn.fetchone_results = [
        {"exists": True},
        {
            "id": 1,
            "diarienummer": "MYH 2024/1",
            "note_text": "Follow up",
            "created_at": "2026-05-27T10:00:00+00:00",
            "updated_at": "2026-05-27T10:00:00+00:00",
        },
    ]

    note = admin_notes.create_application_note(conn, "MYH 2024/1", "  Follow up  ")

    assert note is not None
    assert note["note_text"] == "Follow up"
    combined_sql = "\n".join(sql for sql, _ in conn.executed)
    assert "CREATE TABLE IF NOT EXISTS application_notes" in combined_sql
    assert "SELECT EXISTS" in combined_sql
    assert "INSERT INTO application_notes" in combined_sql
    assert conn.executed[-1][1]["note_text"] == "Follow up"


def test_create_application_note_returns_none_when_application_is_missing() -> None:
    """A missing diarienummer should not create local metadata."""
    conn = RecordingConnection()
    conn.fetchone_results = [{"exists": False}]

    note = admin_notes.create_application_note(conn, "MISSING", "Follow up")

    assert note is None
    combined_sql = "\n".join(sql for sql, _ in conn.executed)
    assert "SELECT EXISTS" in combined_sql
    assert "INSERT INTO application_notes" not in combined_sql


def test_update_application_note_returns_updated_row() -> None:
    """Updating a note should use a parameterized UPDATE."""
    conn = RecordingConnection()
    conn.fetchone_results = [
        {
            "id": 7,
            "diarienummer": "MYH 2024/1",
            "note_text": "Updated",
            "created_at": "2026-05-27T10:00:00+00:00",
            "updated_at": "2026-05-27T11:00:00+00:00",
        }
    ]

    note = admin_notes.update_application_note(conn, 7, " Updated ")

    assert note is not None
    assert note["id"] == 7
    assert "UPDATE application_notes" in conn.executed[-1][0]
    assert conn.executed[-1][1] == {"note_id": 7, "note_text": "Updated"}


def test_delete_application_note_reports_missing_note() -> None:
    """Deleting a missing note should be explicit."""
    conn = RecordingConnection()
    conn.fetchone_results = [None]

    assert admin_notes.delete_application_note(conn, 42) is False
    assert "DELETE FROM application_notes" in conn.executed[-1][0]
