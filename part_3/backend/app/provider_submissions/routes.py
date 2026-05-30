"""Provider-authenticated application submission CRUD routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query, Response, status

from backend.app.dependencies import DatabaseConnection
from backend.app.provider_submissions.dependencies import ProviderSubmissionPrincipal
from backend.app.provider_submissions.models import (
    ProviderSubmissionCreateRequest,
    ProviderSubmissionListResponse,
    ProviderSubmissionResponse,
    ProviderSubmissionStatus,
    ProviderSubmissionUpdateRequest,
)
from backend.app.provider_submissions.repositories import (
    EmptyProviderSubmissionUpdateError,
    ProviderSubmissionStateError,
    create_provider_submission,
    delete_provider_submission,
    get_provider_submission,
    list_provider_submissions,
    submit_provider_submission,
    update_provider_submission,
)


router = APIRouter(prefix="/provider/submissions", tags=["provider submissions"])
SubmissionId = Annotated[UUID, Path(description="Provider submission id.")]


def _not_found() -> HTTPException:
    """Build an ownership-safe not-found response."""
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider submission was not found.")


def _state_conflict(exc: ProviderSubmissionStateError) -> HTTPException:
    """Translate invalid workflow operations to a safe standardized error."""
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("", response_model=ProviderSubmissionResponse, status_code=status.HTTP_201_CREATED)
def create_submission(
    payload: ProviderSubmissionCreateRequest,
    conn: DatabaseConnection,
    provider: ProviderSubmissionPrincipal,
) -> dict:
    """Create a draft application submission owned by the authenticated provider."""
    return create_provider_submission(conn, identity=provider, payload=payload)


@router.get("", response_model=ProviderSubmissionListResponse)
def list_submissions(
    conn: DatabaseConnection,
    provider: ProviderSubmissionPrincipal,
    submission_status: Annotated[
        ProviderSubmissionStatus | None,
        Query(alias="status", description="Optional provider submission status filter."),
    ] = None,
    target_year: Annotated[int | None, Query(ge=2020, le=2100)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    """List only submissions owned by the authenticated provider."""
    items = list_provider_submissions(
        conn,
        provider_id=provider.provider_id,
        status=submission_status,
        target_year=target_year,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "limit": limit, "offset": offset}


@router.get("/{submission_id}", response_model=ProviderSubmissionResponse)
def read_submission(
    submission_id: SubmissionId,
    conn: DatabaseConnection,
    provider: ProviderSubmissionPrincipal,
) -> dict:
    """Read one own provider submission without leaking other providers' ids."""
    submission = get_provider_submission(conn, provider_id=provider.provider_id, submission_id=str(submission_id))
    if submission is None:
        raise _not_found()
    return submission


@router.patch("/{submission_id}", response_model=ProviderSubmissionResponse)
def patch_submission(
    submission_id: SubmissionId,
    payload: ProviderSubmissionUpdateRequest,
    conn: DatabaseConnection,
    provider: ProviderSubmissionPrincipal,
) -> dict:
    """Update editable fields on one own draft or needs_changes submission."""
    try:
        submission = update_provider_submission(
            conn,
            provider_id=provider.provider_id,
            submission_id=str(submission_id),
            payload=payload,
        )
    except EmptyProviderSubmissionUpdateError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ProviderSubmissionStateError as exc:
        raise _state_conflict(exc) from exc
    if submission is None:
        raise _not_found()
    return submission


@router.delete("/{submission_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_submission(
    submission_id: SubmissionId,
    conn: DatabaseConnection,
    provider: ProviderSubmissionPrincipal,
) -> Response:
    """Hard-delete one own draft submission."""
    try:
        deleted = delete_provider_submission(conn, provider_id=provider.provider_id, submission_id=str(submission_id))
    except ProviderSubmissionStateError as exc:
        raise _state_conflict(exc) from exc
    if deleted is None:
        raise _not_found()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{submission_id}/submit", response_model=ProviderSubmissionResponse)
def submit_submission(
    submission_id: SubmissionId,
    conn: DatabaseConnection,
    provider: ProviderSubmissionPrincipal,
) -> dict:
    """Submit or resubmit one own editable submission for admin review."""
    try:
        submission = submit_provider_submission(
            conn,
            provider_id=provider.provider_id,
            submission_id=str(submission_id),
            actor_user_id=str(provider.user_id),
        )
    except ProviderSubmissionStateError as exc:
        raise _state_conflict(exc) from exc
    if submission is None:
        raise _not_found()
    return submission
