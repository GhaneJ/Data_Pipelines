"""Service functions for local protected admin notes."""

from __future__ import annotations

from typing import Any

import psycopg


MAX_NOTE_TEXT_LENGTH = 2000

APPLICATION_NOTES_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS application_notes (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    diarienummer TEXT NOT NULL,
    note_text TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT application_notes_diarienummer_not_blank CHECK (btrim(diarienummer) <> ''),
    CONSTRAINT application_notes_note_text_not_blank CHECK (btrim(note_text) <> '')
);
"""

APPLICATION_NOTES_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_application_notes_diarienummer
    ON application_notes (diarienummer);
"""

APPLICATION_NOTE_SELECT_SQL = """
SELECT
    id,
    diarienummer,
    note_text,
    created_at,
    updated_at
FROM application_notes
"""


def normalize_note_text(note_text: str) -> str:
    """Return a trimmed note value or fail with an explainable error."""
    cleaned = note_text.strip()
    if not cleaned:
        raise ValueError("note_text must not be empty.")
    if len(cleaned) > MAX_NOTE_TEXT_LENGTH:
        raise ValueError(f"note_text must be at most {MAX_NOTE_TEXT_LENGTH} characters.")
    return cleaned


def ensure_application_notes_table(conn: psycopg.Connection[dict[str, Any]]) -> None:
    """Create the local admin metadata table if the database predates 3.12."""
    with conn.cursor() as cursor:
        cursor.execute(APPLICATION_NOTES_SCHEMA_SQL)
        cursor.execute(APPLICATION_NOTES_INDEX_SQL)


def application_exists(conn: psycopg.Connection[dict[str, Any]], diarienummer: str) -> bool:
    """Return whether the curated applications table contains this diarienummer."""
    with conn.cursor() as cursor:
        cursor.execute("SELECT EXISTS (SELECT 1 FROM applications WHERE diarienummer = %(diarienummer)s);", {"diarienummer": diarienummer})
        row = cursor.fetchone()
    return bool(row["exists"] if isinstance(row, dict) else row[0]) if row is not None else False


def list_application_notes(
    conn: psycopg.Connection[dict[str, Any]],
    diarienummer: str,
) -> list[dict[str, Any]] | None:
    """Return notes for one existing application, or None if the application is missing."""
    ensure_application_notes_table(conn)
    if not application_exists(conn, diarienummer):
        return None

    sql = f"""
{APPLICATION_NOTE_SELECT_SQL}
WHERE diarienummer = %(diarienummer)s
ORDER BY created_at DESC, id DESC;
"""
    with conn.cursor() as cursor:
        cursor.execute(sql, {"diarienummer": diarienummer})
        return list(cursor.fetchall())


def create_application_note(
    conn: psycopg.Connection[dict[str, Any]],
    diarienummer: str,
    note_text: str,
) -> dict[str, Any] | None:
    """Create one note for an existing application, or None if the application is missing."""
    ensure_application_notes_table(conn)
    if not application_exists(conn, diarienummer):
        return None

    cleaned_note = normalize_note_text(note_text)
    sql = f"""
INSERT INTO application_notes (diarienummer, note_text)
VALUES (%(diarienummer)s, %(note_text)s)
RETURNING id, diarienummer, note_text, created_at, updated_at;
"""
    with conn.cursor() as cursor:
        cursor.execute(sql, {"diarienummer": diarienummer, "note_text": cleaned_note})
        return cursor.fetchone()


def update_application_note(
    conn: psycopg.Connection[dict[str, Any]],
    note_id: int,
    note_text: str,
) -> dict[str, Any] | None:
    """Update one existing note and return it, or None if the note is missing."""
    ensure_application_notes_table(conn)
    cleaned_note = normalize_note_text(note_text)
    sql = f"""
UPDATE application_notes
SET note_text = %(note_text)s,
    updated_at = NOW()
WHERE id = %(note_id)s
RETURNING id, diarienummer, note_text, created_at, updated_at;
"""
    with conn.cursor() as cursor:
        cursor.execute(sql, {"note_id": note_id, "note_text": cleaned_note})
        return cursor.fetchone()


def delete_application_note(conn: psycopg.Connection[dict[str, Any]], note_id: int) -> bool:
    """Delete one existing note and report whether anything was removed."""
    ensure_application_notes_table(conn)
    with conn.cursor() as cursor:
        cursor.execute("DELETE FROM application_notes WHERE id = %(note_id)s RETURNING id;", {"note_id": note_id})
        return cursor.fetchone() is not None
