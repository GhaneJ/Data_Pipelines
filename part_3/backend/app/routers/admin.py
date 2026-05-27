"""Protected admin routes for local application metadata."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, status

from backend.app.dependencies import DatabaseConnection
from backend.app.schemas import (
    ApplicationNote,
    ApplicationNoteCreate,
    ApplicationNoteDeleteResult,
    ApplicationNotePatch,
    ApplicationNoteUpdate,
)
from backend.app.security import require_admin_token
from backend.app.services.admin_notes import (
    create_application_note,
    delete_application_note,
    list_application_notes,
    normalize_note_text,
    update_application_note,
)


router = APIRouter(prefix="/admin", tags=["admin"])
AdminToken = Annotated[str, Depends(require_admin_token)]
PositiveNoteId = Annotated[int, Path(gt=0, description="Local admin-note id.")]


def _clean_note_or_400(note_text: str) -> str:
    """Translate note validation into the requested HTTP 400 response."""
    try:
        return normalize_note_text(note_text)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


def _missing_application(diarienummer: str) -> HTTPException:
    """Return the standard missing-application error for admin routes."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Application {diarienummer!r} was not found.",
    )


@router.get("/applications/{diarienummer:path}/notes", response_model=list[ApplicationNote])
def get_application_notes(
    diarienummer: str,
    conn: DatabaseConnection,
    admin_token: AdminToken,
) -> list[dict[str, Any]]:
    """List local admin notes for one existing application."""
    notes = list_application_notes(conn, diarienummer)
    if notes is None:
        raise _missing_application(diarienummer)
    return notes


@router.post(
    "/applications/{diarienummer:path}/notes",
    response_model=ApplicationNote,
    status_code=status.HTTP_201_CREATED,
)
def post_application_note(
    diarienummer: str,
    payload: ApplicationNoteCreate,
    conn: DatabaseConnection,
    admin_token: AdminToken,
) -> dict[str, Any]:
    """Create a local admin note for one existing application."""
    note = create_application_note(conn, diarienummer, _clean_note_or_400(payload.note_text))
    if note is None:
        raise _missing_application(diarienummer)
    return note


@router.put("/notes/{note_id}", response_model=ApplicationNote)
def put_application_note(
    note_id: PositiveNoteId,
    payload: ApplicationNoteUpdate,
    conn: DatabaseConnection,
    admin_token: AdminToken,
) -> dict[str, Any]:
    """Replace one local admin note with a new full note_text value."""
    note = update_application_note(conn, note_id, _clean_note_or_400(payload.note_text))
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Admin note {note_id} was not found.")
    return note


@router.patch("/notes/{note_id}", response_model=ApplicationNote)
def patch_application_note(
    note_id: PositiveNoteId,
    payload: ApplicationNotePatch,
    conn: DatabaseConnection,
    admin_token: AdminToken,
) -> dict[str, Any]:
    """Partially update one local admin note.

    The note model currently has only one editable field, so PATCH updates
    note_text when it is provided and rejects empty patch bodies clearly.
    """
    if payload.note_text is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PATCH requires note_text because no other editable note fields exist.",
        )

    note = update_application_note(conn, note_id, _clean_note_or_400(payload.note_text))
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Admin note {note_id} was not found.")
    return note


@router.delete("/notes/{note_id}", response_model=ApplicationNoteDeleteResult)
def delete_admin_note(
    note_id: PositiveNoteId,
    conn: DatabaseConnection,
    admin_token: AdminToken,
) -> dict[str, Any]:
    """Delete one local admin note."""
    deleted = delete_application_note(conn, note_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Admin note {note_id} was not found.")
    return {"note_id": note_id, "deleted": True}
