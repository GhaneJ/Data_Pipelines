"""Repository helpers for provider-created application submissions."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import psycopg

from backend.app.admin_reviews.models import ReviewActorRole, ReviewEventAction
from backend.app.provider_submissions.models import (
    ProviderSubmissionCreateRequest,
    ProviderSubmissionIdentity,
    ProviderSubmissionStatus,
    ProviderSubmissionUpdateRequest,
)

ProviderSubmissionConnection = psycopg.Connection[dict[str, Any]]

PROVIDER_SUBMISSION_SELECT_COLUMNS = """
    id,
    provider_id,
    provider_name,
    created_by_user_id,
    status,
    target_year,
    education_name,
    education_area,
    municipality,
    region,
    yh_points,
    study_form,
    study_pace_percent,
    head_provider_type,
    description,
    notes,
    submitted_at,
    review_started_at,
    reviewed_by_user_id,
    reviewed_at,
    review_notes,
    created_at,
    updated_at
"""

UPDATABLE_FIELDS = (
    "target_year",
    "education_name",
    "education_area",
    "municipality",
    "region",
    "yh_points",
    "study_form",
    "study_pace_percent",
    "head_provider_type",
    "description",
    "notes",
)

PROVIDER_EDITABLE_STATUSES = {
    ProviderSubmissionStatus.DRAFT.value,
    ProviderSubmissionStatus.NEEDS_CHANGES.value,
}


class ProviderSubmissionStateError(ValueError):
    """Raised when a requested workflow operation is not valid for the status."""


class EmptyProviderSubmissionUpdateError(ValueError):
    """Raised when no editable fields are supplied for a patch."""


def _normalize_row(row: dict[str, Any] | None) -> dict[str, Any] | None:
    """Return a row with stable string ids for API responses and tests."""
    if row is None:
        return None
    normalized = dict(row)
    for field in ("id", "created_by_user_id", "reviewed_by_user_id"):
        if normalized.get(field) is not None:
            normalized[field] = str(normalized[field])
    return normalized


def get_provider_name(conn: ProviderSubmissionConnection, provider_id: str) -> str | None:
    """Resolve provider display name from the curated providers table when possible."""
    try:
        numeric_provider_id = int(provider_id)
    except (TypeError, ValueError):
        return None

    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT utbildningsanordnare
            FROM providers
            WHERE provider_id = %(provider_id)s;
            """,
            {"provider_id": numeric_provider_id},
        )
        row = cursor.fetchone()
    if row is None:
        return None
    return str(row["utbildningsanordnare"])


def create_provider_submission(
    conn: ProviderSubmissionConnection,
    *,
    identity: ProviderSubmissionIdentity,
    payload: ProviderSubmissionCreateRequest,
) -> dict[str, Any]:
    """Create one provider-owned draft submission."""
    submission_id = str(uuid4())
    values = payload.model_dump()
    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            INSERT INTO provider_application_submissions (
                id,
                provider_id,
                provider_name,
                created_by_user_id,
                status,
                target_year,
                education_name,
                education_area,
                municipality,
                region,
                yh_points,
                study_form,
                study_pace_percent,
                head_provider_type,
                description,
                notes
            )
            VALUES (
                %(id)s,
                %(provider_id)s,
                %(provider_name)s,
                %(created_by_user_id)s,
                %(status)s,
                %(target_year)s,
                %(education_name)s,
                %(education_area)s,
                %(municipality)s,
                %(region)s,
                %(yh_points)s,
                %(study_form)s,
                %(study_pace_percent)s,
                %(head_provider_type)s,
                %(description)s,
                %(notes)s
            )
            RETURNING {PROVIDER_SUBMISSION_SELECT_COLUMNS};
            """,
            {
                "id": submission_id,
                "provider_id": identity.provider_id,
                "provider_name": identity.provider_name,
                "created_by_user_id": str(identity.user_id),
                "status": ProviderSubmissionStatus.DRAFT.value,
                **values,
            },
        )
        row = cursor.fetchone()
    if row is None:
        raise RuntimeError("Provider submission insertion did not return a row.")
    return _normalize_row(row) or row


def list_provider_submissions(
    conn: ProviderSubmissionConnection,
    *,
    provider_id: str,
    status: ProviderSubmissionStatus | None = None,
    target_year: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """List submissions for the authenticated provider only."""
    where_parts = ["provider_id = %(provider_id)s"]
    params: dict[str, Any] = {"provider_id": provider_id, "limit": limit, "offset": offset}
    if status is not None:
        where_parts.append("status = %(status)s")
        params["status"] = status.value if isinstance(status, ProviderSubmissionStatus) else str(status)
    if target_year is not None:
        where_parts.append("target_year = %(target_year)s")
        params["target_year"] = target_year

    where_sql = " AND ".join(where_parts)
    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT {PROVIDER_SUBMISSION_SELECT_COLUMNS}
            FROM provider_application_submissions
            WHERE {where_sql}
            ORDER BY created_at DESC, id DESC
            LIMIT %(limit)s OFFSET %(offset)s;
            """,
            params,
        )
        return [_normalize_row(row) or row for row in cursor.fetchall()]


def get_provider_submission(
    conn: ProviderSubmissionConnection,
    *,
    provider_id: str,
    submission_id: str,
) -> dict[str, Any] | None:
    """Return one provider-owned submission or None when missing/not owned."""
    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT {PROVIDER_SUBMISSION_SELECT_COLUMNS}
            FROM provider_application_submissions
            WHERE id = %(id)s
              AND provider_id = %(provider_id)s;
            """,
            {"id": submission_id, "provider_id": provider_id},
        )
        return _normalize_row(cursor.fetchone())


def _ensure_provider_editable(row: dict[str, Any], operation: str) -> None:
    if row["status"] not in PROVIDER_EDITABLE_STATUSES:
        raise ProviderSubmissionStateError(
            f"Only draft or needs_changes provider submissions can be {operation}."
        )


def _ensure_draft(row: dict[str, Any], operation: str) -> None:
    if row["status"] != ProviderSubmissionStatus.DRAFT.value:
        raise ProviderSubmissionStateError(f"Only draft provider submissions can be {operation}.")


def _editable_update_fields(payload: ProviderSubmissionUpdateRequest) -> dict[str, Any]:
    values = payload.model_dump(exclude_unset=True)
    allowed_values = {key: value for key, value in values.items() if key in UPDATABLE_FIELDS}
    if not allowed_values:
        raise EmptyProviderSubmissionUpdateError("At least one editable field is required.")
    return allowed_values


def update_provider_submission(
    conn: ProviderSubmissionConnection,
    *,
    provider_id: str,
    submission_id: str,
    payload: ProviderSubmissionUpdateRequest,
) -> dict[str, Any] | None:
    """Update one provider-owned draft or needs_changes submission."""
    existing = get_provider_submission(conn, provider_id=provider_id, submission_id=submission_id)
    if existing is None:
        return None
    _ensure_provider_editable(existing, "updated")
    values = _editable_update_fields(payload)
    assignments = ",\n                ".join(f"{field} = %({field})s" for field in values)
    params = {"id": submission_id, "provider_id": provider_id, **values}

    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            UPDATE provider_application_submissions
            SET {assignments},
                updated_at = NOW()
            WHERE id = %(id)s
              AND provider_id = %(provider_id)s
              AND status IN ('draft', 'needs_changes')
            RETURNING {PROVIDER_SUBMISSION_SELECT_COLUMNS};
            """,
            params,
        )
        row = cursor.fetchone()
    if row is None:
        raise ProviderSubmissionStateError("Only draft or needs_changes provider submissions can be updated.")
    return _normalize_row(row)


def delete_provider_submission(
    conn: ProviderSubmissionConnection,
    *,
    provider_id: str,
    submission_id: str,
) -> bool | None:
    """Hard-delete one provider-owned draft submission.

    Returns None when the submission is missing/not owned, True when deleted,
    and raises ProviderSubmissionStateError when a non-draft record is targeted.
    """
    existing = get_provider_submission(conn, provider_id=provider_id, submission_id=submission_id)
    if existing is None:
        return None
    _ensure_draft(existing, "deleted")

    with conn.cursor() as cursor:
        cursor.execute(
            """
            DELETE FROM provider_application_submissions
            WHERE id = %(id)s
              AND provider_id = %(provider_id)s
              AND status = 'draft'
            RETURNING id;
            """,
            {"id": submission_id, "provider_id": provider_id},
        )
        return cursor.fetchone() is not None


def create_review_event(
    conn: ProviderSubmissionConnection,
    *,
    submission_id: str,
    actor_user_id: str | None,
    actor_role: ReviewActorRole,
    action: ReviewEventAction,
    from_status: str | None,
    to_status: str,
    notes: str | None = None,
) -> dict[str, Any]:
    """Write one review/status-transition audit event."""
    event_id = str(uuid4())
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO provider_submission_review_events (
                id,
                submission_id,
                actor_user_id,
                actor_role,
                action,
                from_status,
                to_status,
                notes
            )
            VALUES (
                %(id)s,
                %(submission_id)s,
                %(actor_user_id)s,
                %(actor_role)s,
                %(action)s,
                %(from_status)s,
                %(to_status)s,
                %(notes)s
            )
            RETURNING id, submission_id, actor_user_id, actor_role, action, from_status, to_status, notes, created_at;
            """,
            {
                "id": event_id,
                "submission_id": submission_id,
                "actor_user_id": actor_user_id,
                "actor_role": actor_role.value,
                "action": action.value,
                "from_status": from_status,
                "to_status": to_status,
                "notes": notes,
            },
        )
        row = cursor.fetchone()
    if row is None:
        raise RuntimeError("Review event insertion did not return a row.")
    normalized = dict(row)
    for field in ("id", "submission_id", "actor_user_id"):
        if normalized.get(field) is not None:
            normalized[field] = str(normalized[field])
    return normalized


def submit_provider_submission(
    conn: ProviderSubmissionConnection,
    *,
    provider_id: str,
    submission_id: str,
    actor_user_id: str | None = None,
) -> dict[str, Any] | None:
    """Mark one provider-owned draft or needs_changes submission as submitted."""
    existing = get_provider_submission(conn, provider_id=provider_id, submission_id=submission_id)
    if existing is None:
        return None
    if existing["status"] not in {ProviderSubmissionStatus.DRAFT.value, ProviderSubmissionStatus.NEEDS_CHANGES.value}:
        raise ProviderSubmissionStateError("Only draft or needs_changes provider submissions can be submitted.")

    from_status = existing["status"]
    action = (
        ReviewEventAction.RESUBMITTED
        if from_status == ProviderSubmissionStatus.NEEDS_CHANGES.value
        else ReviewEventAction.SUBMITTED
    )
    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            UPDATE provider_application_submissions
            SET status = 'submitted',
                submitted_at = NOW(),
                updated_at = NOW()
            WHERE id = %(id)s
              AND provider_id = %(provider_id)s
              AND status IN ('draft', 'needs_changes')
            RETURNING {PROVIDER_SUBMISSION_SELECT_COLUMNS};
            """,
            {"id": submission_id, "provider_id": provider_id},
        )
        row = cursor.fetchone()
    if row is None:
        raise ProviderSubmissionStateError("Only draft or needs_changes provider submissions can be submitted.")

    create_review_event(
        conn,
        submission_id=submission_id,
        actor_user_id=actor_user_id,
        actor_role=ReviewActorRole.PROVIDER,
        action=action,
        from_status=from_status,
        to_status=ProviderSubmissionStatus.SUBMITTED.value,
    )
    return _normalize_row(row)
