"""Repository helpers for admin review of provider submissions."""

from __future__ import annotations

from typing import Any

import psycopg

from backend.app.admin_reviews.models import AdminReviewRequest, ReviewActorRole, ReviewEventAction
from backend.app.provider_submissions.models import ProviderSubmissionStatus
from backend.app.provider_submissions.repositories import (
    PROVIDER_SUBMISSION_SELECT_COLUMNS,
    ProviderSubmissionStateError,
    create_review_event,
)

AdminReviewConnection = psycopg.Connection[dict[str, Any]]

DEFAULT_REVIEW_QUEUE_STATUSES = (
    ProviderSubmissionStatus.SUBMITTED.value,
    ProviderSubmissionStatus.UNDER_REVIEW.value,
    ProviderSubmissionStatus.NEEDS_CHANGES.value,
)


def _normalize_row(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    normalized = dict(row)
    for field in ("id", "created_by_user_id", "reviewed_by_user_id"):
        if normalized.get(field) is not None:
            normalized[field] = str(normalized[field])
    return normalized


def _normalize_event(row: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(row)
    for field in ("id", "submission_id", "actor_user_id"):
        if normalized.get(field) is not None:
            normalized[field] = str(normalized[field])
    return normalized


def list_admin_provider_submissions(
    conn: AdminReviewConnection,
    *,
    status: ProviderSubmissionStatus | None = None,
    provider_id: str | None = None,
    target_year: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """List provider submissions for the admin review queue."""
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    where_parts: list[str] = []
    if status is None:
        where_parts.append("status = ANY(%(default_statuses)s)")
        params["default_statuses"] = list(DEFAULT_REVIEW_QUEUE_STATUSES)
    else:
        where_parts.append("status = %(status)s")
        params["status"] = status.value if isinstance(status, ProviderSubmissionStatus) else str(status)
    if provider_id:
        where_parts.append("provider_id = %(provider_id)s")
        params["provider_id"] = provider_id
    if target_year is not None:
        where_parts.append("target_year = %(target_year)s")
        params["target_year"] = target_year

    where_sql = " AND ".join(where_parts) if where_parts else "TRUE"
    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT {PROVIDER_SUBMISSION_SELECT_COLUMNS}
            FROM provider_application_submissions
            WHERE {where_sql}
            ORDER BY submitted_at DESC NULLS LAST, created_at DESC, id DESC
            LIMIT %(limit)s OFFSET %(offset)s;
            """,
            params,
        )
        return [_normalize_row(row) or row for row in cursor.fetchall()]


def get_admin_provider_submission(
    conn: AdminReviewConnection,
    *,
    submission_id: str,
) -> dict[str, Any] | None:
    """Return any provider submission for an admin caller."""
    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT {PROVIDER_SUBMISSION_SELECT_COLUMNS}
            FROM provider_application_submissions
            WHERE id = %(id)s;
            """,
            {"id": submission_id},
        )
        return _normalize_row(cursor.fetchone())


def list_review_events(conn: AdminReviewConnection, *, submission_id: str) -> list[dict[str, Any]] | None:
    """Return ordered review events for one submission, or None if missing."""
    if get_admin_provider_submission(conn, submission_id=submission_id) is None:
        return None
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, submission_id, actor_user_id, actor_role, action, from_status, to_status, notes, created_at
            FROM provider_submission_review_events
            WHERE submission_id = %(submission_id)s
            ORDER BY created_at ASC, id ASC;
            """,
            {"submission_id": submission_id},
        )
        return [_normalize_event(row) for row in cursor.fetchall()]


def _admin_transition(
    conn: AdminReviewConnection,
    *,
    submission_id: str,
    admin_user_id: str,
    payload: AdminReviewRequest,
    allowed_from: set[str],
    to_status: ProviderSubmissionStatus,
    action: ReviewEventAction,
    set_reviewed_at: bool,
) -> dict[str, Any] | None:
    existing = get_admin_provider_submission(conn, submission_id=submission_id)
    if existing is None:
        return None
    from_status = str(existing["status"])
    if from_status not in allowed_from:
        allowed = ", ".join(sorted(allowed_from))
        raise ProviderSubmissionStateError(
            f"Cannot {action.value.replace('_', ' ')} provider submission from status {from_status!r}; expected one of: {allowed}."
        )

    reviewed_at_sql = "NOW()" if set_reviewed_at else "reviewed_at"
    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            UPDATE provider_application_submissions
            SET status = %(to_status)s,
                review_started_at = COALESCE(review_started_at, NOW()),
                reviewed_by_user_id = %(admin_user_id)s,
                reviewed_at = {reviewed_at_sql},
                review_notes = %(review_notes)s,
                updated_at = NOW()
            WHERE id = %(id)s
              AND status = %(from_status)s
            RETURNING {PROVIDER_SUBMISSION_SELECT_COLUMNS};
            """,
            {
                "id": submission_id,
                "from_status": from_status,
                "to_status": to_status.value,
                "admin_user_id": admin_user_id,
                "review_notes": payload.review_notes,
            },
        )
        row = cursor.fetchone()
    if row is None:
        raise ProviderSubmissionStateError("Provider submission status changed before the review action completed.")

    create_review_event(
        conn,
        submission_id=submission_id,
        actor_user_id=admin_user_id,
        actor_role=ReviewActorRole.ADMIN,
        action=action,
        from_status=from_status,
        to_status=to_status.value,
        notes=payload.review_notes,
    )
    return _normalize_row(row)


def start_review(
    conn: AdminReviewConnection,
    *,
    submission_id: str,
    admin_user_id: str,
    payload: AdminReviewRequest,
) -> dict[str, Any] | None:
    """Start admin review for a submitted provider submission."""
    return _admin_transition(
        conn,
        submission_id=submission_id,
        admin_user_id=admin_user_id,
        payload=payload,
        allowed_from={ProviderSubmissionStatus.SUBMITTED.value},
        to_status=ProviderSubmissionStatus.UNDER_REVIEW,
        action=ReviewEventAction.REVIEW_STARTED,
        set_reviewed_at=False,
    )


def request_changes(
    conn: AdminReviewConnection,
    *,
    submission_id: str,
    admin_user_id: str,
    payload: AdminReviewRequest,
) -> dict[str, Any] | None:
    """Return a submission to the provider for corrections."""
    return _admin_transition(
        conn,
        submission_id=submission_id,
        admin_user_id=admin_user_id,
        payload=payload,
        allowed_from={ProviderSubmissionStatus.SUBMITTED.value, ProviderSubmissionStatus.UNDER_REVIEW.value},
        to_status=ProviderSubmissionStatus.NEEDS_CHANGES,
        action=ReviewEventAction.CHANGES_REQUESTED,
        set_reviewed_at=True,
    )


def approve_submission(
    conn: AdminReviewConnection,
    *,
    submission_id: str,
    admin_user_id: str,
    payload: AdminReviewRequest,
) -> dict[str, Any] | None:
    """Approve a submitted/under-review submission as a workflow decision only."""
    return _admin_transition(
        conn,
        submission_id=submission_id,
        admin_user_id=admin_user_id,
        payload=payload,
        allowed_from={ProviderSubmissionStatus.SUBMITTED.value, ProviderSubmissionStatus.UNDER_REVIEW.value},
        to_status=ProviderSubmissionStatus.APPROVED,
        action=ReviewEventAction.APPROVED,
        set_reviewed_at=True,
    )


def reject_submission(
    conn: AdminReviewConnection,
    *,
    submission_id: str,
    admin_user_id: str,
    payload: AdminReviewRequest,
) -> dict[str, Any] | None:
    """Reject a submitted/under-review submission as a workflow decision only."""
    return _admin_transition(
        conn,
        submission_id=submission_id,
        admin_user_id=admin_user_id,
        payload=payload,
        allowed_from={ProviderSubmissionStatus.SUBMITTED.value, ProviderSubmissionStatus.UNDER_REVIEW.value},
        to_status=ProviderSubmissionStatus.REJECTED,
        action=ReviewEventAction.REJECTED,
        set_reviewed_at=True,
    )
