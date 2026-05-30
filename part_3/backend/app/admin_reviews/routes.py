"""Admin-authenticated review routes for provider submissions."""

from __future__ import annotations

from typing import Annotated, Callable
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query, status

from backend.app.admin_reviews.models import (
    AdminProviderSubmissionListResponse,
    AdminProviderSubmissionResponse,
    AdminReviewRequest,
    ReviewEventResponse,
)
from backend.app.admin_reviews.repositories import (
    approve_submission,
    get_admin_provider_submission,
    list_admin_provider_submissions,
    list_review_events,
    reject_submission,
    request_changes,
    start_review,
)
from backend.app.auth.dependencies import AdminRoutePrincipal
from backend.app.dependencies import DatabaseConnection
from backend.app.provider_submissions.models import ProviderSubmissionStatus
from backend.app.provider_submissions.repositories import ProviderSubmissionStateError


router = APIRouter(prefix="/admin/provider-submissions", tags=["admin provider submissions"])
SubmissionId = Annotated[UUID, Path(description="Provider submission id.")]
AdminPrincipal = AdminRoutePrincipal


def _user_id_from_subject(subject: str) -> str:
    prefix = "user:"
    if not subject.startswith(prefix):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authenticated admin subject is invalid.")
    try:
        return str(UUID(subject.removeprefix(prefix)))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authenticated admin subject is invalid.") from exc


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider submission was not found.")


def _state_conflict(exc: ProviderSubmissionStateError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("", response_model=AdminProviderSubmissionListResponse)
def list_review_queue(
    conn: DatabaseConnection,
    admin_principal: AdminPrincipal,
    submission_status: Annotated[
        ProviderSubmissionStatus | None,
        Query(alias="status", description="Optional provider submission status filter."),
    ] = None,
    provider_id: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    target_year: Annotated[int | None, Query(ge=2020, le=2100)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    """List provider submissions for admin review."""
    items = list_admin_provider_submissions(
        conn,
        status=submission_status,
        provider_id=provider_id.strip() if provider_id else None,
        target_year=target_year,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "limit": limit, "offset": offset}


@router.get("/{submission_id}", response_model=AdminProviderSubmissionResponse)
def read_provider_submission(
    submission_id: SubmissionId,
    conn: DatabaseConnection,
    admin_principal: AdminPrincipal,
) -> dict:
    """Read any provider submission for admin review."""
    submission = get_admin_provider_submission(conn, submission_id=str(submission_id))
    if submission is None:
        raise _not_found()
    return submission


@router.get("/{submission_id}/events", response_model=list[ReviewEventResponse])
def read_review_events(
    submission_id: SubmissionId,
    conn: DatabaseConnection,
    admin_principal: AdminPrincipal,
) -> list[dict]:
    """Read ordered review events for one provider submission."""
    events = list_review_events(conn, submission_id=str(submission_id))
    if events is None:
        raise _not_found()
    return events


def _run_transition(
    *,
    action: Callable[..., dict | None],
    submission_id: UUID,
    payload: AdminReviewRequest,
    conn: DatabaseConnection,
    admin_principal: AdminPrincipal,
) -> dict:
    try:
        submission = action(
            conn,
            submission_id=str(submission_id),
            admin_user_id=_user_id_from_subject(admin_principal.subject),
            payload=payload,
        )
    except ProviderSubmissionStateError as exc:
        raise _state_conflict(exc) from exc
    if submission is None:
        raise _not_found()
    return submission


@router.post("/{submission_id}/start-review", response_model=AdminProviderSubmissionResponse)
def post_start_review(
    submission_id: SubmissionId,
    payload: AdminReviewRequest,
    conn: DatabaseConnection,
    admin_principal: AdminPrincipal,
) -> dict:
    """Move a submitted provider submission into under_review."""
    return _run_transition(
        action=start_review,
        submission_id=submission_id,
        payload=payload,
        conn=conn,
        admin_principal=admin_principal,
    )


@router.post("/{submission_id}/request-changes", response_model=AdminProviderSubmissionResponse)
def post_request_changes(
    submission_id: SubmissionId,
    payload: AdminReviewRequest,
    conn: DatabaseConnection,
    admin_principal: AdminPrincipal,
) -> dict:
    """Return a submitted/under-review provider submission for changes."""
    return _run_transition(
        action=request_changes,
        submission_id=submission_id,
        payload=payload,
        conn=conn,
        admin_principal=admin_principal,
    )


@router.post("/{submission_id}/approve", response_model=AdminProviderSubmissionResponse)
def post_approve(
    submission_id: SubmissionId,
    payload: AdminReviewRequest,
    conn: DatabaseConnection,
    admin_principal: AdminPrincipal,
) -> dict:
    """Approve a provider submission as a workflow decision only."""
    return _run_transition(
        action=approve_submission,
        submission_id=submission_id,
        payload=payload,
        conn=conn,
        admin_principal=admin_principal,
    )


@router.post("/{submission_id}/reject", response_model=AdminProviderSubmissionResponse)
def post_reject(
    submission_id: SubmissionId,
    payload: AdminReviewRequest,
    conn: DatabaseConnection,
    admin_principal: AdminPrincipal,
) -> dict:
    """Reject a provider submission as a workflow decision only."""
    return _run_transition(
        action=reject_submission,
        submission_id=submission_id,
        payload=payload,
        conn=conn,
        admin_principal=admin_principal,
    )
